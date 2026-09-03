from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.signal import find_peaks

from engine.scoring import (
    ATTENTION_GROUPS,
    EMOTION_GROUPS,
    FUNCTIONAL_GROUPS,
    ActivationContext,
)

PEAK_PROMINENCE = 0.5


@dataclass
class TimelinePoint:
    timestep: int
    time_s: float
    scroll_position_px: float
    overall_intensity: float
    attention_intensity: float
    emotion_intensity: float
    language_intensity: float
    region_breakdown: dict[str, float]


@dataclass
class PeakAnnotation:
    timestep: int
    time_s: float
    scroll_position_px: float
    intensity: float
    dominant_group: str
    description: str


@dataclass
class TimelineData:
    series: list[TimelinePoint]
    peaks: list[PeakAnnotation]
    duration_s: float


_PEAK_TEMPLATES = {
    "visual": "Visual cortex peak at {time:.1f}s",
    "attention": "Attention network peak at {time:.1f}s",
    "emotional": "Emotional network peak at {time:.1f}s",
    "language": "Language network peak at {time:.1f}s",
    "default_mode": "Default-mode network peak at {time:.1f}s",
}


def _alignment_row(segment_alignment: list[dict[str, Any]], t: int) -> dict[str, Any]:
    for row in segment_alignment:
        if int(row.get("timestep", -1)) == t:
            return row
    if t < len(segment_alignment):
        return segment_alignment[t]
    return {}


def build_timeline(
    ctx: ActivationContext, segment_alignment: list[dict[str, Any]]
) -> TimelineData:
    att_idx = ctx.vertices_for(ATTENTION_GROUPS)
    emo_idx = ctx.vertices_for(EMOTION_GROUPS)
    lang_idx = ctx.group_vertices["language"]
    overall = ctx.overall_series()

    series: list[TimelinePoint] = []
    for t in range(ctx.n_timesteps):
        row = _alignment_row(segment_alignment, t)
        breakdown = {
            g: ctx.score_at(ctx.raw_mean_at(t, ctx.group_vertices[g])) for g in FUNCTIONAL_GROUPS
        }
        series.append(
            TimelinePoint(
                timestep=t,
                time_s=float(row.get("stimulus_time_s", t)),
                scroll_position_px=float(row.get("scroll_position_px", 0.0)),
                overall_intensity=ctx.score_at(float(overall[t])),
                attention_intensity=ctx.score_at(ctx.raw_mean_at(t, att_idx)),
                emotion_intensity=ctx.score_at(ctx.raw_mean_at(t, emo_idx)),
                language_intensity=ctx.score_at(ctx.raw_mean_at(t, lang_idx)),
                region_breakdown=breakdown,
            )
        )

    overall_scores = np.array([p.overall_intensity for p in series])
    peak_indices, _ = find_peaks(overall_scores, prominence=PEAK_PROMINENCE)
    peaks: list[PeakAnnotation] = []
    for ix in peak_indices:
        point = series[int(ix)]
        dominant = max(point.region_breakdown, key=point.region_breakdown.get)
        peaks.append(
            PeakAnnotation(
                timestep=point.timestep,
                time_s=point.time_s,
                scroll_position_px=point.scroll_position_px,
                intensity=point.overall_intensity,
                dominant_group=dominant,
                description=_PEAK_TEMPLATES[dominant].format(time=point.time_s),
            )
        )

    duration = max((p.time_s for p in series), default=0.0)
    return TimelineData(series=series, peaks=peaks, duration_s=float(duration))
