"""Report compiler: assembles all engine outputs into a self-contained JSON report."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from config import settings
from engine.atlas import Atlas, load_atlas
from engine.dark_patterns import DarkPatternReport, detect_dark_patterns
from engine.heatmap import mean_vertex_colors, generate_2d_projections
from engine.overlay import ElementOverlay, build_overlay, overlay_to_json
from engine.scoring import ScoreReport, compute_scores
from engine.timeline import TimelineData, build_timeline

logger = logging.getLogger(__name__)


@dataclass
class AnalysisReport:
    job_id: str
    url: str
    scores: ScoreReport
    dark_patterns: DarkPatternReport
    timeline: TimelineData
    overlay: list[ElementOverlay]
    heatmap_colors_path: str | None = None
    projection_paths: dict[str, str] = field(default_factory=dict)
    template_summaries: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def _generate_summaries(scores: ScoreReport, dark_patterns: DarkPatternReport) -> dict[str, str]:
    att = scores.attention_score
    emo = scores.emotion_score
    impact = scores.impact_score

    if att >= 6.5 and emo >= 6.5:
        overall = (
            "This site uses strong visual elements that both grab attention and "
            "trigger emotional responses. The combination suggests highly engineered "
            "engagement design."
        )
    elif att >= 6.5 and emo < 6.5:
        overall = (
            "Visually engaging design that captures focus without heavy emotional "
            "manipulation. The site relies primarily on visual attention mechanisms."
        )
    elif att < 6.5 and emo >= 6.5:
        overall = (
            "Subtle emotional triggers present despite unremarkable visual design. "
            "The site may use text or imagery that evokes emotional responses without "
            "relying on visual complexity."
        )
    else:
        overall = (
            "Moderate brain engagement overall. The site does not show strong "
            "attention-capturing or emotionally triggering patterns in its design."
        )

    attention_summary = (
        f"Attention score: {att:.1f}/10. "
        + (
            "Visual and prefrontal cortex regions show elevated activation, "
            "indicating the design effectively captures and holds visual attention."
            if att >= 6.0
            else "Visual cortex activation is within normal range, suggesting "
            "the design does not heavily rely on attention-grabbing techniques."
        )
    )

    emotion_summary = (
        f"Emotion score: {emo:.1f}/10. "
        + (
            "Limbic and insular cortex show heightened activation, suggesting "
            "the site's content triggers significant emotional processing."
            if emo >= 6.0
            else "Emotional processing regions show moderate activation, "
            "indicating limited emotional manipulation in the design."
        )
    )

    impact_summary = (
        f"Overall Brain Impact: {impact:.1f}/10. "
        + (
            "The combined attention, emotional, and temporal dynamics suggest "
            "this site has a strong neurological footprint."
            if impact >= 6.5
            else "The overall neurological impact of this site is moderate."
        )
    )

    dark_summary = dark_patterns.summary

    variance_desc = ""
    tv = scores.temporal_variance
    if tv >= 7.0:
        variance_desc = (
            "High temporal variance detected — the site's brain impact fluctuates "
            "significantly during the scroll, suggesting strategically placed "
            "attention peaks."
        )
    elif tv >= 4.0:
        variance_desc = (
            "Moderate temporal variance in brain activation across the scroll "
            "duration, with some notable fluctuations."
        )
    else:
        variance_desc = (
            "Relatively stable brain activation throughout the scroll, without "
            "dramatic peaks or valleys."
        )

    return {
        "overall": overall,
        "attention": attention_summary,
        "emotion": emotion_summary,
        "impact": impact_summary,
        "dark_patterns": dark_summary,
        "temporal_dynamics": variance_desc,
    }


def compile_report(
    job_id: str,
    url: str,
    predictions: np.ndarray,
    segment_alignment: list[dict[str, Any]],
    capture_dir: str | Path,
    colormap: str = "viridis",
    viewport_height: int = 900,
    capture_metadata: dict[str, Any] | None = None,
) -> AnalysisReport:
    """Run the full deterministic analysis pipeline and assemble the report.

    This is the main entry point for Phase 3 core engine processing.
    """
    predictions = np.asarray(predictions, dtype=np.float64)
    cap = Path(capture_dir)
    reports_dir = Path(settings.DATA_DIR) / "reports" / job_id
    reports_dir.mkdir(parents=True, exist_ok=True)

    atlas = load_atlas()

    logger.info("Computing scores for job %s ...", job_id)
    scores = compute_scores(predictions, atlas)

    text_path = cap / "visible_text.txt"
    extracted_text = ""
    if text_path.exists():
        extracted_text = text_path.read_text(encoding="utf-8")

    bbox_path = cap / "bounding_boxes.json"
    flat_boxes: list[dict[str, Any]] = []
    if bbox_path.exists():
        raw = json.loads(bbox_path.read_text(encoding="utf-8"))
        for sample in raw.get("samples", []):
            flat_boxes.extend(sample.get("boxes", []))

    logger.info("Detecting dark patterns for job %s ...", job_id)
    dark_report = detect_dark_patterns(extracted_text, flat_boxes)

    logger.info("Building timeline for job %s ...", job_id)
    timeline = build_timeline(predictions, atlas, segment_alignment)

    logger.info("Building overlay for job %s ...", job_id)
    overlay = build_overlay(
        predictions, atlas, segment_alignment, bbox_path, viewport_height
    )

    logger.info("Generating heatmap colors for job %s ...", job_id)
    mean_colors = mean_vertex_colors(predictions, colormap)
    colors_path = reports_dir / "heatmap_colors.npy"
    np.save(str(colors_path), mean_colors)

    logger.info("Generating 2D projections for job %s ...", job_id)
    mean_activations = np.mean(predictions, axis=0)
    proj_dir = reports_dir / "projections"
    proj_paths = generate_2d_projections(mean_activations, str(proj_dir), colormap)

    summaries = _generate_summaries(scores, dark_report)

    meta: dict[str, Any] = {
        "url": url,
        "capture_date": datetime.now(timezone.utc).isoformat(),
        "n_timesteps": int(predictions.shape[0]),
        "n_vertices": int(predictions.shape[1]),
        "colormap": colormap,
        "viewport_height": viewport_height,
    }
    if capture_metadata:
        meta["capture_duration_s"] = capture_metadata.get("duration_s")
        meta["viewport_w"] = capture_metadata.get("viewport_w")
        meta["viewport_h"] = capture_metadata.get("viewport_h")

    report = AnalysisReport(
        job_id=job_id,
        url=url,
        scores=scores,
        dark_patterns=dark_report,
        timeline=timeline,
        overlay=overlay,
        heatmap_colors_path=str(colors_path),
        projection_paths=proj_paths,
        template_summaries=summaries,
        metadata=meta,
    )

    _save_report_json(report, reports_dir / "report.json")
    return report


def _save_report_json(report: AnalysisReport, path: Path) -> None:
    """Serialize the report to a self-contained JSON file for the frontend."""
    data: dict[str, Any] = {
        "job_id": report.job_id,
        "url": report.url,
        "scores": {
            "attention_score": report.scores.attention_score,
            "emotion_score": report.scores.emotion_score,
            "impact_score": report.scores.impact_score,
            "temporal_variance": report.scores.temporal_variance,
            "region_breakdown": report.scores.region_breakdown,
            "per_timestep_scores": report.scores.per_timestep_scores,
        },
        "dark_patterns": {
            "patterns": [asdict(p) for p in report.dark_patterns.patterns],
            "score": report.dark_patterns.score,
            "summary": report.dark_patterns.summary,
        },
        "timeline": {
            "series": [asdict(pt) for pt in report.timeline.series],
            "peaks": [asdict(pk) for pk in report.timeline.peaks],
            "duration_s": report.timeline.duration_s,
        },
        "overlay": overlay_to_json(report.overlay),
        "heatmap_colors_path": report.heatmap_colors_path,
        "projection_paths": report.projection_paths,
        "template_summaries": report.template_summaries,
        "metadata": report.metadata,
    }
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    logger.info("Report saved to %s (%.1f KB)", path, path.stat().st_size / 1024)


def load_report(job_id: str) -> dict[str, Any] | None:
    """Load a previously compiled report from disk."""
    path = Path(settings.DATA_DIR) / "reports" / job_id / "report.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
