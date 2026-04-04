from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.signal import find_peaks

from engine.atlas import Atlas

from engine.scoring import (
    FUNCTIONAL_GROUPS,
    _combined_group_vertices,
    _normalize_activation,
    _vertex_mean_at_timestep,
)


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
    intensity: float
    dominant_group: str
    description: str


@dataclass
class TimelineData:
    series: list[TimelinePoint]
    peaks: list[PeakAnnotation]
    duration_s: float


def detect_peaks(series: list[float], prominence: float = 0.5) -> list[int]:
    arr = np.asarray(series, dtype=np.float64)
    if arr.size == 0:
        return []
    peaks, _ = find_peaks(arr, prominence=prominence)
    return [int(i) for i in peaks]


def _alignment_for_timestep(
    segment_alignment: list[dict[str, Any]], t: int, n_t: int
) -> dict[str, Any]:
    by_ts = {int(a["timestep"]): a for a in segment_alignment if "timestep" in a}
    if t in by_ts:
        return by_ts[t]
    if len(segment_alignment) == n_t:
        return segment_alignment[t]
    if segment_alignment:
        return segment_alignment[min(t, len(segment_alignment) - 1)]
    return {}


def _scroll_px(row: dict[str, Any]) -> float:
    v = row.get("scroll_position_px")
    return float(v) if v is not None else 0.0


def _time_s(row: dict[str, Any], fallback: float) -> float:
    if "stimulus_time_s" in row:
        return float(row["stimulus_time_s"])
    return fallback


def _dominant_group(intensities: dict[str, float]) -> str:
    if not intensities:
        return "attention"
    return max(intensities, key=intensities.get)  # type: ignore[arg-type]


def _peak_description(dominant: str, time_s: float) -> str:
    templates = {
        "visual": "Peak attention at {time:.1f}s — strong visual cortex activation",
        "attention": "Peak attention at {time:.1f}s — strong attention network activation",
        "emotional": "Peak emotional response at {time:.1f}s — strong emotional network activation",
        "language": "Peak language processing at {time:.1f}s — strong language network activation",
        "default_mode": "Peak default-mode activity at {time:.1f}s — strong default-mode activation",
    }
    return templates.get(dominant, templates["attention"]).format(time=time_s)


def build_timeline(
    predictions: np.ndarray,
    atlas: Atlas,
    segment_alignment: list[dict[str, Any]],
    k: float = 1.0,
    center: float = 0.0,
) -> TimelineData:
    predictions = np.asarray(predictions, dtype=np.float64)
    if predictions.ndim != 2:
        raise ValueError("predictions must be 2D (n_timesteps, n_vertices)")

    n_t = predictions.shape[0]
    group_idx = {
        g: atlas.get_functional_group_vertices(g) for g in FUNCTIONAL_GROUPS
    }
    att_idx = _combined_group_vertices(atlas, ("visual", "attention"))
    emo_idx = atlas.get_functional_group_vertices("emotional")
    lang_idx = atlas.get_functional_group_vertices("language")

    series: list[TimelinePoint] = []
    overall_series: list[float] = []

    for t in range(n_t):
        row = _alignment_for_timestep(segment_alignment, t, n_t)
        stim_time = _time_s(row, float(t))
        scroll = _scroll_px(row)

        region_intensity: dict[str, float] = {}
        for g in FUNCTIONAL_GROUPS:
            raw_g = _vertex_mean_at_timestep(predictions, t, group_idx[g])
            region_intensity[g] = _normalize_activation(
                raw_g, predictions, k, center
            )

        overall_raw = float(np.mean(predictions[t]))
        att_raw = _vertex_mean_at_timestep(predictions, t, att_idx)
        emo_raw = _vertex_mean_at_timestep(predictions, t, emo_idx)
        lang_raw = _vertex_mean_at_timestep(predictions, t, lang_idx)

        overall_i = _normalize_activation(overall_raw, predictions, k, center)
        attention_i = _normalize_activation(att_raw, predictions, k, center)
        emotion_i = _normalize_activation(emo_raw, predictions, k, center)
        language_i = _normalize_activation(lang_raw, predictions, k, center)

        overall_series.append(overall_i)
        series.append(
            TimelinePoint(
                timestep=t,
                time_s=stim_time,
                scroll_position_px=scroll,
                overall_intensity=overall_i,
                attention_intensity=attention_i,
                emotion_intensity=emotion_i,
                language_intensity=language_i,
                region_breakdown=region_intensity,
            )
        )

    peak_ixs = detect_peaks(overall_series, prominence=0.5)
    peaks: list[PeakAnnotation] = []
    for ix in peak_ixs:
        pt = series[ix]
        dom = _dominant_group(pt.region_breakdown)
        peaks.append(
            PeakAnnotation(
                timestep=pt.timestep,
                time_s=pt.time_s,
                intensity=pt.overall_intensity,
                dominant_group=dom,
                description=_peak_description(dom, pt.time_s),
            )
        )

    if series:
        duration_s = float(max(p.time_s for p in series))
    else:
        duration_s = 0.0

    return TimelineData(series=series, peaks=peaks, duration_s=duration_s)
