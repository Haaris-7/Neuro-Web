"""Time-segment → DOM region intensity mapping for website overlay heatmap."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from engine.atlas import Atlas
from engine.scoring import FUNCTIONAL_GROUPS, _normalize_activation, _vertex_mean_at_timestep

logger = logging.getLogger(__name__)


@dataclass
class ElementOverlay:
    tag: str
    bbox: dict[str, float]
    intensity: float
    attention_contrib: float
    emotion_contrib: float
    visible_timesteps: list[int] = field(default_factory=list)


def _load_bounding_boxes(bbox_path: str | Path) -> list[dict[str, Any]]:
    path = Path(bbox_path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("samples", [])


def _scroll_range_for_timestep(
    timestep: int,
    segment_alignment: list[dict[str, Any]],
    viewport_height: int = 900,
) -> tuple[float, float]:
    """Determine visible scroll range (top, bottom) for a given timestep."""
    scroll_y = 0.0
    for entry in segment_alignment:
        if entry.get("timestep") == timestep:
            scroll_y = float(entry.get("scroll_position_px", 0))
            break
    return scroll_y, scroll_y + viewport_height


def _element_key(box: dict[str, Any]) -> str:
    return f"{box.get('tag', '')}:{box.get('x', 0):.0f}:{box.get('y', 0):.0f}:{box.get('width', 0):.0f}:{box.get('height', 0):.0f}"


def _element_in_viewport(
    box: dict[str, Any],
    scroll_top: float,
    scroll_bottom: float,
) -> bool:
    """Check if a DOM element is visible within the viewport scroll range.

    Bounding boxes from capture use viewport-relative coordinates and record
    the scroll_y at capture time, so element absolute position =
    box_y + box_scroll_y.
    """
    box_scroll = float(box.get("scroll_y", 0))
    abs_y = float(box.get("y", 0)) + box_scroll
    abs_bottom = abs_y + float(box.get("height", 0))
    return abs_bottom > scroll_top and abs_y < scroll_bottom


def build_overlay(
    predictions: np.ndarray,
    atlas: Atlas,
    segment_alignment: list[dict[str, Any]],
    bounding_boxes_path: str | Path,
    viewport_height: int = 900,
) -> list[ElementOverlay]:
    """Map brain activation time segments to DOM elements for overlay rendering.

    For each scroll segment, determines which DOM elements were visible,
    aggregates brain activation, and assigns per-region intensity to each element.
    """
    predictions = np.asarray(predictions, dtype=np.float64)
    if predictions.ndim != 2:
        raise ValueError("predictions must be 2-D (n_timesteps, n_vertices)")

    samples = _load_bounding_boxes(bounding_boxes_path)
    if not samples:
        return []

    n_timesteps = predictions.shape[0]

    att_groups = ("visual", "attention")
    att_idx = np.array([], dtype=np.intp)
    for g in att_groups:
        try:
            gv = atlas.get_functional_group_vertices(g)
            if gv.size > 0:
                att_idx = np.unique(np.concatenate([att_idx, gv])) if att_idx.size else gv
        except KeyError:
            pass
    emo_idx = atlas.get_functional_group_vertices("emotional")

    element_data: dict[str, dict[str, Any]] = {}

    for t in range(n_timesteps):
        scroll_top, scroll_bottom = _scroll_range_for_timestep(
            t, segment_alignment, viewport_height
        )

        closest_sample = _find_closest_sample(samples, scroll_top)
        if not closest_sample:
            continue

        overall_raw = float(np.mean(predictions[t]))
        att_raw = _vertex_mean_at_timestep(predictions, t, att_idx) if att_idx.size else 0.0
        emo_raw = _vertex_mean_at_timestep(predictions, t, emo_idx) if emo_idx.size else 0.0

        intensity = _normalize_activation(overall_raw, predictions)
        att_intensity = _normalize_activation(att_raw, predictions) if att_idx.size else 0.0
        emo_intensity = _normalize_activation(emo_raw, predictions) if emo_idx.size else 0.0

        boxes = closest_sample.get("boxes", [])
        for box in boxes:
            if not _element_in_viewport(box, scroll_top, scroll_bottom):
                continue
            key = _element_key(box)
            if key not in element_data:
                element_data[key] = {
                    "tag": str(box.get("tag", "")),
                    "bbox": {
                        "x": float(box.get("x", 0)),
                        "y": float(box.get("y", 0)) + float(box.get("scroll_y", 0)),
                        "width": float(box.get("width", 0)),
                        "height": float(box.get("height", 0)),
                    },
                    "intensities": [],
                    "att_contribs": [],
                    "emo_contribs": [],
                    "timesteps": [],
                }
            ed = element_data[key]
            ed["intensities"].append(intensity)
            ed["att_contribs"].append(att_intensity)
            ed["emo_contribs"].append(emo_intensity)
            ed["timesteps"].append(t)

    result: list[ElementOverlay] = []
    for _key, ed in element_data.items():
        result.append(
            ElementOverlay(
                tag=ed["tag"],
                bbox=ed["bbox"],
                intensity=float(np.max(ed["intensities"])) if ed["intensities"] else 0.0,
                attention_contrib=float(np.max(ed["att_contribs"])) if ed["att_contribs"] else 0.0,
                emotion_contrib=float(np.max(ed["emo_contribs"])) if ed["emo_contribs"] else 0.0,
                visible_timesteps=ed["timesteps"],
            )
        )

    result.sort(key=lambda e: e.intensity, reverse=True)
    return result


def _find_closest_sample(
    samples: list[dict[str, Any]], scroll_y: float
) -> dict[str, Any] | None:
    if not samples:
        return None
    return min(samples, key=lambda s: abs(float(s.get("scroll_y", 0)) - scroll_y))


def overlay_to_json(elements: list[ElementOverlay]) -> list[dict[str, Any]]:
    """Serialize overlay elements for the frontend."""
    return [asdict(e) for e in elements]
