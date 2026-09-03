"""Turn capture artifacts into per-second brain activation predictions.

One TRIBE v2 ``predict`` call receives every enabled modality on a shared
timeline, so the model fuses video and text the way it was trained to instead
of averaging two unimodal passes. Rows are aligned to stimulus time and to the
scroll position recorded during capture.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np

from config import settings
from engine.atlas import load_atlas
from pipeline.media import probe_duration
from pipeline.model_manager import ModelManager
from pipeline.tribe_events import build_events, schedule_words, text_blocks_from_dom

logger = logging.getLogger(__name__)

HEMODYNAMIC_OFFSET_S = 5.0
EXPECTED_N_VERTICES = 20484


def run_inference(job_id: str) -> dict[str, Any]:
    data_root = Path(settings.DATA_DIR).resolve()
    capture_dir = (data_root / "captures" / job_id).resolve()
    preds_dir = (data_root / "predictions" / job_id).resolve()
    for p in (capture_dir, preds_dir):
        p.relative_to(data_root)
    preds_dir.mkdir(parents=True, exist_ok=True)

    artifacts = _load_capture(capture_dir)
    modalities = settings.TRIBE_MODALITIES
    backend = settings.INFERENCE_BACKEND

    t0 = time.monotonic()
    if backend == "mock":
        preds, starts, n_words = _predict_mock(job_id, artifacts)
    else:
        preds, starts, n_words = _predict_tribe(artifacts, modalities)
    elapsed = time.monotonic() - t0

    if preds.ndim != 2 or preds.shape[0] == 0:
        raise RuntimeError(f"Inference produced an unexpected array of shape {preds.shape}")
    if preds.shape[1] != EXPECTED_N_VERTICES:
        logger.warning(
            "Expected %d fsaverage5 vertices, got %d", EXPECTED_N_VERTICES, preds.shape[1]
        )

    alignment = _build_alignment(starts, artifacts["scroll_timeline"])
    np.savez_compressed(preds_dir / "predictions.npz", preds=preds.astype(np.float32))
    (preds_dir / "segment_alignment.json").write_text(json.dumps(alignment, indent=2))

    metadata = {
        "job_id": job_id,
        "inference_backend": backend,
        "modalities": list(modalities) if backend == "tribe" else ["synthetic"],
        "predictions_path": str(preds_dir / "predictions.npz"),
        "segment_alignment": alignment,
        "n_timesteps": int(preds.shape[0]),
        "n_vertices": int(preds.shape[1]),
        "n_words": n_words,
        "video_duration_s": artifacts["duration_s"],
        "hemodynamic_offset_s": HEMODYNAMIC_OFFSET_S,
        "inference_time_s": round(elapsed, 2),
    }
    (preds_dir / "inference_metadata.json").write_text(json.dumps(metadata, indent=2))
    logger.info(
        "Inference (%s) done for %s in %.1fs: %d timesteps x %d vertices",
        backend,
        job_id,
        elapsed,
        preds.shape[0],
        preds.shape[1],
    )
    return metadata


def _read_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def _load_capture(capture_dir: Path) -> dict[str, Any]:
    """Load capture artifacts with the scroll timeline expressed in video time."""
    if not capture_dir.is_dir():
        raise FileNotFoundError(f"Capture directory not found: {capture_dir}")
    video = capture_dir / "capture.mp4"
    if not video.is_file():
        video = capture_dir / "capture.webm"
    if not video.is_file():
        raise FileNotFoundError(f"Capture video not found in {capture_dir}")

    capture_meta = _read_json(capture_dir / "capture.json", {})
    dom = _read_json(capture_dir / "dom.json", {})
    timeline = _read_json(capture_dir / "scroll_timeline.json", [])
    offset_s = float(capture_meta.get("video_offset_s", 0.0))
    if offset_s > 0 and timeline:
        timeline = [{"time_ms": 0, "scroll_y": 0.0}] + [
            {"time_ms": float(s["time_ms"]) + offset_s * 1000.0, "scroll_y": s["scroll_y"]}
            for s in timeline
        ]

    duration = probe_duration(video)
    if duration is None:
        duration = (
            float(timeline[-1]["time_ms"]) / 1000.0
            if timeline
            else float(capture_meta.get("duration_s") or settings.CAPTURE_DURATION)
        )
    viewport_h = float(dom.get("viewport", {}).get("height", settings.CAPTURE_VIEWPORT_H))
    return {
        "video": video,
        "dom": dom,
        "scroll_timeline": timeline,
        "duration_s": round(float(duration), 3),
        "viewport_h": viewport_h,
    }


def _word_rows(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    return schedule_words(
        text_blocks_from_dom(artifacts["dom"]),
        artifacts["scroll_timeline"],
        artifacts["viewport_h"],
        artifacts["duration_s"],
        words_per_minute=settings.TEXT_READING_WPM,
        context_words=settings.TEXT_CONTEXT_WORDS,
    )


def _predict_tribe(
    artifacts: dict[str, Any], modalities: tuple[str, ...]
) -> tuple[np.ndarray, list[float], int]:
    mgr = ModelManager.get()
    if not mgr.is_loaded or mgr.model is None:
        raise RuntimeError(mgr.error or "TRIBE v2 model is not loaded")

    words = _word_rows(artifacts) if "text" in modalities else []
    if "text" in modalities and not words:
        logger.warning("Text modality enabled but no readable words were scheduled")
    events = build_events(
        video_path=artifacts["video"] if "video" in modalities else None,
        word_rows=words,
    )
    logger.info(
        "Running TRIBE v2 on %d events (modalities=%s, words=%d, video=%.1fs)",
        len(events),
        ",".join(modalities),
        len(words),
        artifacts["duration_s"],
    )
    preds, segments = mgr.model.predict(events=events, verbose=False)
    starts = [float(getattr(seg, "start", i)) for i, seg in enumerate(segments)]
    return np.asarray(preds, dtype=np.float32), starts, len(words)


def _predict_mock(job_id: str, artifacts: dict[str, Any]) -> tuple[np.ndarray, list[float], int]:
    from pipeline.mock_backend import mock_predict

    words = _word_rows(artifacts)
    preds, starts = mock_predict(
        job_id=job_id,
        duration_s=artifacts["duration_s"],
        atlas=load_atlas(),
        scroll_timeline=artifacts["scroll_timeline"],
        dom=artifacts["dom"],
        viewport_h=artifacts["viewport_h"],
    )
    return preds, starts, len(words)


def _scroll_at(timeline: list[dict[str, float]], t_s: float) -> float:
    if not timeline:
        return 0.0
    ms = t_s * 1000.0
    times = [float(s["time_ms"]) for s in timeline]
    ys = [float(s["scroll_y"]) for s in timeline]
    return float(np.interp(ms, times, ys))


def _build_alignment(
    starts: list[float], scroll_timeline: list[dict[str, float]]
) -> list[dict[str, Any]]:
    alignment = []
    for t, start in enumerate(starts):
        alignment.append(
            {
                "timestep": t,
                "stimulus_time_s": round(start, 3),
                "brain_response_time_s": round(start + HEMODYNAMIC_OFFSET_S, 3),
                "scroll_position_px": round(_scroll_at(scroll_timeline, start), 2),
            }
        )
    return alignment
