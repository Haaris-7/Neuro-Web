"""TRIBE v2 inference orchestration: capture artifacts → brain activation predictions.

Handles video and text modality prediction, weighted combination, timeline alignment
with hemodynamic offset, and storage of results as compressed numpy arrays.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np

from config import settings
from pipeline.model_manager import ModelManager
from pipeline.tribe_wrapper import get_video_only_events

logger = logging.getLogger(__name__)

HEMODYNAMIC_OFFSET_S = 5.0


def run_inference(job_id: str) -> dict:
    """Run TRIBE v2 inference on captured artifacts for a job.

    Returns metadata dict with prediction paths and segment alignment.

    Raises RuntimeError if model isn't loaded or inference fails.
    """
    mgr = ModelManager.get()
    if not mgr.is_loaded or mgr.model is None:
        raise RuntimeError(
            mgr.error or "TRIBE v2 model not loaded. Run `make setup` or check GPU."
        )

    capture_dir = Path(settings.DATA_DIR) / "captures" / job_id
    preds_dir = Path(settings.DATA_DIR) / "predictions" / job_id
    preds_dir.mkdir(parents=True, exist_ok=True)

    _validate_capture_dir(capture_dir, preds_dir)

    video_path = capture_dir / "capture.webm"
    text_path = capture_dir / "visible_text.txt"
    scroll_timeline_path = capture_dir / "scroll_timeline.json"

    model = mgr.model

    video_preds, video_segments = _predict_video(model, video_path)
    text_preds, text_segments = _predict_text(model, text_path)

    combined, alignment = _combine_predictions(
        video_preds,
        video_segments,
        text_preds,
        text_segments,
        video_weight=settings.VIDEO_WEIGHT,
        text_weight=settings.TEXT_WEIGHT,
    )

    scroll_timeline = _load_scroll_timeline(scroll_timeline_path)
    alignment = _align_to_scroll_timeline(alignment, scroll_timeline)

    _save_predictions(
        preds_dir,
        video_preds=video_preds,
        text_preds=text_preds,
        combined_preds=combined,
        alignment=alignment,
    )

    metadata = {
        "job_id": job_id,
        "predictions_dir": str(preds_dir),
        "video_preds_path": str(preds_dir / "video_preds.npz"),
        "text_preds_path": str(preds_dir / "text_preds.npz"),
        "combined_preds_path": str(preds_dir / "combined_preds.npz"),
        "segment_alignment": alignment,
        "n_timesteps": combined.shape[0],
        "n_vertices": combined.shape[1],
        "video_weight": settings.VIDEO_WEIGHT,
        "text_weight": settings.TEXT_WEIGHT,
        "hemodynamic_offset_s": HEMODYNAMIC_OFFSET_S,
    }

    meta_path = preds_dir / "inference_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, default=str))

    logger.info(
        "Inference complete for job %s — %d timesteps × %d vertices",
        job_id,
        combined.shape[0],
        combined.shape[1],
    )
    return metadata


def _validate_capture_dir(capture_dir: Path, preds_dir: Path) -> None:
    """Ensure capture artifacts exist and paths are safe."""
    data_root = Path(settings.DATA_DIR).resolve()
    for p in (capture_dir, preds_dir):
        resolved = p.resolve()
        if not str(resolved).startswith(str(data_root)):
            raise ValueError(f"Path traversal blocked: {p}")

    if not capture_dir.exists():
        raise FileNotFoundError(f"Capture directory not found: {capture_dir}")

    video = capture_dir / "capture.webm"
    text = capture_dir / "visible_text.txt"
    if not video.exists():
        raise FileNotFoundError(f"Capture video not found: {video}")
    if not text.exists():
        raise FileNotFoundError(f"Extracted text not found: {text}")


def _predict_video(model, video_path: Path) -> tuple[np.ndarray, list]:
    """Run TRIBE v2 prediction on video modality using custom video-only wrapper."""
    logger.info("Running video modality prediction...")
    t0 = time.monotonic()

    video_df = get_video_only_events(str(video_path))
    preds, segments = model.predict(events=video_df)

    elapsed = time.monotonic() - t0
    preds_array = np.asarray(preds, dtype=np.float32)
    logger.info(
        "Video prediction done in %.1fs — shape %s",
        elapsed,
        preds_array.shape,
    )
    return preds_array, segments


def _predict_text(model, text_path: Path) -> tuple[np.ndarray, list]:
    """Run TRIBE v2 prediction on text modality using standard API."""
    logger.info("Running text modality prediction...")
    t0 = time.monotonic()

    text_df = model.get_events_dataframe(text_path=str(text_path))
    preds, segments = model.predict(events=text_df)

    elapsed = time.monotonic() - t0
    preds_array = np.asarray(preds, dtype=np.float32)
    logger.info(
        "Text prediction done in %.1fs — shape %s",
        elapsed,
        preds_array.shape,
    )
    return preds_array, segments


def _combine_predictions(
    video_preds: np.ndarray,
    video_segments: list,
    text_preds: np.ndarray,
    text_segments: list,
    *,
    video_weight: float,
    text_weight: float,
) -> tuple[np.ndarray, list[dict]]:
    """Combine video and text predictions via weighted average.

    If modalities have different numbers of timesteps, the shorter one is
    zero-padded to match the longer. Weights are re-normalized for timesteps
    where only one modality contributes.
    """
    n_video = video_preds.shape[0]
    n_text = text_preds.shape[0]
    n_vertices = video_preds.shape[1]
    n_max = max(n_video, n_text)

    video_padded = np.zeros((n_max, n_vertices), dtype=np.float32)
    text_padded = np.zeros((n_max, n_vertices), dtype=np.float32)
    video_padded[:n_video] = video_preds
    text_padded[:n_text] = text_preds

    combined = np.zeros((n_max, n_vertices), dtype=np.float32)
    for t in range(n_max):
        has_video = t < n_video
        has_text = t < n_text
        if has_video and has_text:
            w_total = video_weight + text_weight
            combined[t] = (
                video_padded[t] * video_weight + text_padded[t] * text_weight
            ) / w_total
        elif has_video:
            combined[t] = video_padded[t]
        elif has_text:
            combined[t] = text_padded[t]

    alignment = _build_segment_alignment(
        n_max, video_segments, text_segments
    )

    logger.info(
        "Combined predictions: video(%d) + text(%d) → %d timesteps "
        "(weights: video=%.2f, text=%.2f)",
        n_video,
        n_text,
        n_max,
        video_weight,
        text_weight,
    )
    return combined, alignment


def _build_segment_alignment(
    n_timesteps: int,
    video_segments: list,
    text_segments: list,
) -> list[dict]:
    """Build per-timestep alignment metadata from segment objects."""
    alignment = []
    for t in range(n_timesteps):
        entry: dict = {"timestep": t}

        if t < len(video_segments):
            seg = video_segments[t]
            start = getattr(seg, "start", None)
            duration = getattr(seg, "duration", None)
            if start is not None:
                entry["video_start_s"] = float(start)
            if duration is not None:
                entry["video_duration_s"] = float(duration)

        if t < len(text_segments):
            seg = text_segments[t]
            start = getattr(seg, "start", None)
            duration = getattr(seg, "duration", None)
            if start is not None:
                entry["text_start_s"] = float(start)
            if duration is not None:
                entry["text_duration_s"] = float(duration)

        stimulus_start = entry.get("video_start_s", entry.get("text_start_s", 0.0))
        entry["stimulus_time_s"] = stimulus_start
        entry["brain_response_time_s"] = stimulus_start + HEMODYNAMIC_OFFSET_S

        alignment.append(entry)

    return alignment


def _load_scroll_timeline(path: Path) -> list[dict] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        logger.warning("Could not parse scroll timeline at %s", path)
        return None


def _align_to_scroll_timeline(
    alignment: list[dict],
    scroll_timeline: list[dict] | None,
) -> list[dict]:
    """Enrich alignment entries with scroll position from capture timeline."""
    if not scroll_timeline:
        return alignment

    for entry in alignment:
        stimulus_t = entry.get("stimulus_time_s", 0.0)
        stimulus_ms = stimulus_t * 1000.0
        closest = min(
            scroll_timeline,
            key=lambda s: abs(s.get("time_ms", 0) - stimulus_ms),
        )
        entry["scroll_position_px"] = closest.get("scroll_y", 0)
        entry["scroll_timestamp_ms"] = closest.get("time_ms", 0)

    return alignment


def _save_predictions(
    preds_dir: Path,
    *,
    video_preds: np.ndarray,
    text_preds: np.ndarray,
    combined_preds: np.ndarray,
    alignment: list[dict],
) -> None:
    """Store predictions as compressed numpy archives."""
    np.savez_compressed(preds_dir / "video_preds.npz", preds=video_preds)
    np.savez_compressed(preds_dir / "text_preds.npz", preds=text_preds)
    np.savez_compressed(preds_dir / "combined_preds.npz", preds=combined_preds)

    alignment_path = preds_dir / "segment_alignment.json"
    alignment_path.write_text(json.dumps(alignment, indent=2, default=str))

    total_bytes = sum(
        f.stat().st_size for f in preds_dir.iterdir() if f.is_file()
    )
    logger.info(
        "Predictions saved to %s (%.1f MB total)",
        preds_dir,
        total_bytes / (1024 * 1024),
    )
