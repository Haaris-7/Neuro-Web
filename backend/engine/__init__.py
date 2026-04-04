"""Core Engine — deterministic scoring & analytics.

Public API for Phase 3: transforms TRIBE v2 predictions into scores,
heatmaps, dark pattern analysis, and structured reports.
"""

from engine.atlas import Atlas, load_atlas
from engine.dark_patterns import DarkPatternMatch, DarkPatternReport, detect_dark_patterns
from engine.heatmap import (
    activation_to_vertex_colors,
    mean_vertex_colors,
    timestep_vertex_colors,
)
from engine.mesh_export import export_brain_mesh
from engine.overlay import ElementOverlay, build_overlay, overlay_to_json
from engine.report import AnalysisReport, compile_report, load_report
from engine.scoring import ScoreReport, compute_scores
from engine.timeline import (
    PeakAnnotation,
    TimelineData,
    TimelinePoint,
    build_timeline,
)

__all__ = [
    "Atlas",
    "load_atlas",
    "DarkPatternMatch",
    "DarkPatternReport",
    "detect_dark_patterns",
    "activation_to_vertex_colors",
    "mean_vertex_colors",
    "timestep_vertex_colors",
    "export_brain_mesh",
    "ElementOverlay",
    "build_overlay",
    "overlay_to_json",
    "AnalysisReport",
    "compile_report",
    "load_report",
    "ScoreReport",
    "compute_scores",
    "PeakAnnotation",
    "TimelineData",
    "TimelinePoint",
    "build_timeline",
]
