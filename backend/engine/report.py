"""Assemble scores, dark patterns, timeline, overlay and heatmap data into one report."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from config import settings
from engine.atlas import load_atlas
from engine.dark_patterns import DarkPatternReport, detect_dark_patterns
from engine.heatmap import export_vertex_activation, generate_2d_projections
from engine.overlay import ElementOverlay, build_overlay, overlay_to_json
from engine.scoring import ActivationContext, ScoreReport, compute_scores_from_context
from engine.timeline import TimelineData, build_timeline

logger = logging.getLogger(__name__)

REPORT_FILE = "report.json"
DEFAULT_COLORMAP = "viridis"


@dataclass
class AnalysisReport:
    job_id: str
    url: str
    scores: ScoreReport
    dark_patterns: DarkPatternReport
    timeline: TimelineData
    overlay: list[ElementOverlay]
    vertex_activation: dict[str, Any]
    projection_paths: dict[str, str] = field(default_factory=dict)
    template_summaries: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def _level(value: float, high: float, mid: float) -> str:
    if value >= high:
        return "high"
    if value >= mid:
        return "moderate"
    return "low"


def _generate_summaries(scores: ScoreReport, dark: DarkPatternReport) -> dict[str, str]:
    att, emo, impact, tv = (
        scores.attention_score,
        scores.emotion_score,
        scores.impact_score,
        scores.temporal_variance,
    )
    att_level, emo_level = _level(att, 6.5, 4.0), _level(emo, 6.5, 4.0)

    overall = {
        ("high", "high"): (
            "Visual and attention networks and emotion-related regions both stand out, "
            "a profile typical of heavily engineered engagement design."
        ),
        ("high", "moderate"): (
            "The design leans on visual attention capture; emotion-related regions "
            "respond at an ordinary level."
        ),
        ("high", "low"): (
            "Strong visual attention capture with little emotional engagement, "
            "consistent with dense or high-contrast layouts."
        ),
        ("moderate", "high"): (
            "Emotion-related regions dominate the predicted response while visual "
            "attention capture is ordinary, pointing to persuasive copy or imagery."
        ),
        ("low", "high"): (
            "Emotion-related regions respond strongly despite unremarkable visual "
            "capture, suggesting the page works through content rather than layout."
        ),
    }.get(
        (att_level, emo_level),
        "Predicted engagement is moderate: no network stands out sharply relative to "
        "the rest of cortex for this page.",
    )

    attention = f"Attention score {att:.1f}/10. " + {
        "high": "Visual cortex and dorsal attention regions are elevated relative to other networks, "
        "indicating the design pulls and holds visual attention.",
        "moderate": "Visual and attention networks respond about as strongly as the rest of cortex.",
        "low": "Visual and attention networks are comparatively quiet, suggesting a calm layout.",
    }[att_level]

    emotion = f"Emotion score {emo:.1f}/10. " + {
        "high": "Insular, cingulate and orbitofrontal regions are elevated, consistent with "
        "emotionally salient content.",
        "moderate": "Emotion-related regions respond at a typical level for this page.",
        "low": "Emotion-related regions are comparatively quiet.",
    }[emo_level]

    impact_text = f"Brain impact {impact:.1f}/10. " + (
        "The combination of attention capture, emotional response and temporal dynamics "
        "gives this page a strong predicted neural footprint."
        if impact >= 6.5
        else "The predicted neural footprint of this page is moderate."
    )

    temporal = {
        "high": "Activation fluctuates strongly during the scroll, pointing to distinct attention peaks.",
        "moderate": "Activation varies moderately as the page scrolls.",
        "low": "Activation stays fairly even throughout the scroll.",
    }[_level(tv, 7.0, 4.0)]

    return {
        "overall": overall,
        "attention": attention,
        "emotion": emotion,
        "impact": impact_text,
        "dark_patterns": dark.summary,
        "temporal_dynamics": temporal,
    }


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Could not parse %s", path)
        return default


def compile_report(
    *,
    job_id: str,
    url: str,
    predictions: np.ndarray,
    segment_alignment: list[dict[str, Any]],
    capture_dir: Path,
    inference_meta: dict[str, Any],
    capture_meta: dict[str, Any] | None = None,
    colormap: str = DEFAULT_COLORMAP,
) -> AnalysisReport:
    reports_dir = Path(settings.DATA_DIR).resolve() / "reports" / job_id
    reports_dir.mkdir(parents=True, exist_ok=True)
    capture_meta = capture_meta or {}

    atlas = load_atlas()
    ctx = ActivationContext(predictions, atlas)
    viewport_h = float(capture_meta.get("viewport_h") or settings.CAPTURE_VIEWPORT_H)
    viewport_w = float(capture_meta.get("viewport_w") or settings.CAPTURE_VIEWPORT_W)

    dom = _read_json(capture_dir / "dom.json", {})
    text_path = capture_dir / "visible_text.txt"
    visible_text = text_path.read_text(encoding="utf-8") if text_path.is_file() else ""

    logger.info("Scoring job %s", job_id)
    scores = compute_scores_from_context(ctx)
    dark = detect_dark_patterns(visible_text, dom)
    timeline = build_timeline(ctx, segment_alignment)
    overlay = build_overlay(ctx, segment_alignment, dom, viewport_h)
    vertex_meta = export_vertex_activation(ctx.predictions, atlas, reports_dir)
    projections = generate_2d_projections(
        ctx.predictions.mean(axis=0), reports_dir / "projections", colormap
    )

    metadata = {
        "url": url,
        "capture_date": datetime.now(timezone.utc).isoformat(),
        "inference_backend": inference_meta.get("inference_backend", settings.INFERENCE_BACKEND),
        "modalities": inference_meta.get("modalities", []),
        "n_timesteps": ctx.n_timesteps,
        "n_vertices": int(ctx.predictions.shape[1]),
        "n_words": inference_meta.get("n_words"),
        "hemodynamic_offset_s": inference_meta.get("hemodynamic_offset_s"),
        "colormap": colormap,
        "viewport_w": viewport_w,
        "viewport_h": viewport_h,
        "page_height": capture_meta.get("page_height"),
        "capture_duration_s": capture_meta.get("duration_s"),
        "video_duration_s": inference_meta.get("video_duration_s"),
        "atlas": "desikan_killiany",
        "mesh": "fsaverage5",
    }

    report = AnalysisReport(
        job_id=job_id,
        url=url,
        scores=scores,
        dark_patterns=dark,
        timeline=timeline,
        overlay=overlay,
        vertex_activation=vertex_meta,
        projection_paths=projections,
        template_summaries=_generate_summaries(scores, dark),
        metadata=metadata,
    )
    _write_report(report, reports_dir / REPORT_FILE)
    return report


def report_to_dict(report: AnalysisReport) -> dict[str, Any]:
    return {
        "job_id": report.job_id,
        "url": report.url,
        "scores": asdict(report.scores),
        "dark_patterns": {
            "patterns": [asdict(p) for p in report.dark_patterns.patterns],
            "score": report.dark_patterns.score,
            "summary": report.dark_patterns.summary,
            "counts": report.dark_patterns.counts,
        },
        "timeline": {
            "series": [asdict(p) for p in report.timeline.series],
            "peaks": [asdict(p) for p in report.timeline.peaks],
            "duration_s": report.timeline.duration_s,
        },
        "overlay": overlay_to_json(report.overlay),
        "vertex_activation": report.vertex_activation,
        "projection_paths": report.projection_paths,
        "template_summaries": report.template_summaries,
        "metadata": report.metadata,
    }


def _write_report(report: AnalysisReport, path: Path) -> None:
    path.write_text(json.dumps(report_to_dict(report), indent=2), encoding="utf-8")
    logger.info("Report written to %s (%.1f KB)", path, path.stat().st_size / 1024)


def load_report(job_id: str) -> dict[str, Any] | None:
    path = Path(settings.DATA_DIR).resolve() / "reports" / job_id / REPORT_FILE
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
