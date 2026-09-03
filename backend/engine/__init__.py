"""Deterministic analytics on top of TRIBE v2 predictions: scores, dark patterns,
timeline, page overlay and heatmap data."""

from engine.atlas import Atlas, load_atlas
from engine.dark_patterns import DarkPatternMatch, DarkPatternReport, detect_dark_patterns
from engine.heatmap import export_vertex_activation, generate_2d_projections
from engine.mesh_export import ensure_brain_mesh
from engine.overlay import ElementOverlay, build_overlay, overlay_to_json
from engine.report import AnalysisReport, compile_report, load_report, report_to_dict
from engine.scoring import ActivationContext, ScoreReport, compute_scores
from engine.timeline import PeakAnnotation, TimelineData, TimelinePoint, build_timeline

__all__ = [
    "ActivationContext",
    "AnalysisReport",
    "Atlas",
    "DarkPatternMatch",
    "DarkPatternReport",
    "ElementOverlay",
    "PeakAnnotation",
    "ScoreReport",
    "TimelineData",
    "TimelinePoint",
    "build_overlay",
    "build_timeline",
    "compile_report",
    "compute_scores",
    "detect_dark_patterns",
    "ensure_brain_mesh",
    "export_vertex_activation",
    "generate_2d_projections",
    "load_atlas",
    "load_report",
    "overlay_to_json",
    "report_to_dict",
]
