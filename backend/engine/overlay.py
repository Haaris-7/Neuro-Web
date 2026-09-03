"""Map per-timestep brain activation onto the page regions that were on screen."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from engine.scoring import ATTENTION_GROUPS, EMOTION_GROUPS, ActivationContext

MIN_REGION_AREA_PX = 400.0
MAX_REGIONS = 400


@dataclass
class ElementOverlay:
    tag: str
    bbox: dict[str, float]
    fixed: bool
    intensity: float
    attention_contrib: float
    emotion_contrib: float
    visible_timesteps: list[int] = field(default_factory=list)


def _bbox(region: dict[str, Any]) -> dict[str, float]:
    return {
        "x": float(region.get("x", 0.0)),
        "y": float(region.get("y", 0.0)),
        "width": float(region.get("width", 0.0)),
        "height": float(region.get("height", 0.0)),
    }


def _visible(bbox: dict[str, float], fixed: bool, top: float, bottom: float) -> bool:
    if fixed:
        return True
    return bbox["y"] < bottom and bbox["y"] + bbox["height"] > top


def build_overlay(
    ctx: ActivationContext,
    segment_alignment: list[dict[str, Any]],
    dom: dict[str, Any],
    viewport_height: float,
) -> list[ElementOverlay]:
    """Attribute each timestep's activation to the regions visible at that scroll position.

    Intensities are on a 0-1 scale (score / 10) averaged over the timesteps
    during which the element was on screen.
    """
    regions = [
        r for r in dom.get("regions", [])
        if float(r.get("width", 0)) * float(r.get("height", 0)) >= MIN_REGION_AREA_PX
    ][:MAX_REGIONS]
    if not regions:
        return []

    att_idx = ctx.vertices_for(ATTENTION_GROUPS)
    emo_idx = ctx.vertices_for(EMOTION_GROUPS)
    overall = ctx.overall_series()
    scroll_by_t = {
        int(row.get("timestep", i)): float(row.get("scroll_position_px", 0.0))
        for i, row in enumerate(segment_alignment)
    }

    accum: list[dict[str, Any]] = [
        {
            "tag": str(r.get("tag", "")),
            "bbox": _bbox(r),
            "fixed": bool(r.get("fixed", False)),
            "overall": [],
            "att": [],
            "emo": [],
            "t": [],
        }
        for r in regions
    ]
    for t in range(ctx.n_timesteps):
        top = scroll_by_t.get(t, 0.0)
        bottom = top + viewport_height
        overall_i = ctx.score_at(float(overall[t])) / 10.0
        att_i = ctx.score_at(ctx.raw_mean_at(t, att_idx)) / 10.0
        emo_i = ctx.score_at(ctx.raw_mean_at(t, emo_idx)) / 10.0
        for entry in accum:
            if _visible(entry["bbox"], entry["fixed"], top, bottom):
                entry["overall"].append(overall_i)
                entry["att"].append(att_i)
                entry["emo"].append(emo_i)
                entry["t"].append(t)

    result = [
        ElementOverlay(
            tag=e["tag"],
            bbox=e["bbox"],
            fixed=e["fixed"],
            intensity=float(np.mean(e["overall"])),
            attention_contrib=float(np.mean(e["att"])),
            emotion_contrib=float(np.mean(e["emo"])),
            visible_timesteps=e["t"],
        )
        for e in accum
        if e["t"]
    ]
    result.sort(key=lambda e: e.intensity, reverse=True)
    return result


def overlay_to_json(elements: list[ElementOverlay]) -> list[dict[str, Any]]:
    return [asdict(e) for e in elements]
