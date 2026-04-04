from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from engine.atlas import Atlas, load_atlas

FUNCTIONAL_GROUPS = (
    "visual",
    "attention",
    "emotional",
    "language",
    "default_mode",
)

ATTENTION_GROUPS = ("visual", "attention")

__all__ = [
    "ScoreReport",
    "compute_scores",
    "compute_attention_score",
    "compute_emotion_score",
    "compute_impact_score",
    "compute_temporal_variance",
    "compute_region_breakdown",
    "FUNCTIONAL_GROUPS",
    "load_atlas",
]


def _combined_group_vertices(atlas: Atlas, names: tuple[str, ...]) -> np.ndarray:
    parts = [atlas.get_functional_group_vertices(n) for n in names]
    nonempty = [p for p in parts if np.size(p) > 0]
    if not nonempty:
        return np.array([], dtype=np.intp)
    return np.unique(np.concatenate(nonempty))


@dataclass
class ScoreReport:
    attention_score: float
    emotion_score: float
    impact_score: float
    temporal_variance: float
    region_breakdown: list[dict[str, Any]]
    per_timestep_scores: list[dict[str, float]]


def _sigmoid_map(z: float, k: float, center: float) -> float:
    s = 10.0 / (1.0 + float(np.exp(-k * (z - center))))
    return float(np.clip(s, 0.0, 10.0))


def _z_of_scalar(value: float, predictions: np.ndarray) -> float:
    mu = float(np.mean(predictions))
    sigma = float(np.std(predictions)) + 1e-9
    return (value - mu) / sigma


def _normalize_activation(
    raw_mean: float, predictions: np.ndarray, k: float = 1.0, center: float = 0.0
) -> float:
    z = _z_of_scalar(raw_mean, predictions)
    return _sigmoid_map(z, k, center)


def _normalize_temporal_variance_scalar(
    raw_var: float, predictions: np.ndarray, k: float = 1.0, center: float = 0.0
) -> float:
    per_t_spread = np.var(predictions, axis=1)
    ref = float(np.mean(per_t_spread))
    scale = float(np.std(per_t_spread)) + 1e-9
    z = (raw_var - ref) / scale
    return _sigmoid_map(z, k, center)


def _vertex_mean_over_time(
    predictions: np.ndarray, vertex_indices: np.ndarray
) -> float:
    if vertex_indices.size == 0:
        return 0.0
    idx = vertex_indices.astype(np.intp, copy=False)
    subset = predictions[:, idx]
    return float(np.mean(subset))


def _vertex_mean_at_timestep(
    predictions: np.ndarray, t: int, vertex_indices: np.ndarray
) -> float:
    if vertex_indices.size == 0:
        return 0.0
    idx = vertex_indices.astype(np.intp, copy=False)
    return float(np.mean(predictions[t, idx]))


def compute_attention_score(
    predictions: np.ndarray,
    atlas: Atlas,
    k: float = 1.0,
    center: float = 0.0,
) -> float:
    all_idx = _combined_group_vertices(atlas, ATTENTION_GROUPS)
    if all_idx.size == 0:
        return 0.0
    raw = _vertex_mean_over_time(predictions, all_idx)
    return _normalize_activation(raw, predictions, k, center)


def compute_emotion_score(
    predictions: np.ndarray,
    atlas: Atlas,
    k: float = 1.0,
    center: float = 0.0,
) -> float:
    idx = atlas.get_functional_group_vertices("emotional")
    raw = _vertex_mean_over_time(predictions, idx)
    return _normalize_activation(raw, predictions, k, center)


def compute_temporal_variance(
    predictions: np.ndarray, k: float = 1.0, center: float = 0.0
) -> float:
    overall_per_t = np.mean(predictions, axis=1)
    raw = float(np.var(overall_per_t))
    return _normalize_temporal_variance_scalar(raw, predictions, k, center)


def compute_impact_score(
    attention: float, emotion: float, temporal_variance: float
) -> float:
    v = 0.4 * attention + 0.4 * emotion + 0.2 * temporal_variance
    return float(np.clip(v, 0.0, 10.0))


def compute_region_breakdown(
    predictions: np.ndarray,
    atlas: Atlas,
    k: float = 1.0,
    center: float = 0.0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in FUNCTIONAL_GROUPS:
        idx = atlas.get_functional_group_vertices(group)
        raw = _vertex_mean_over_time(predictions, idx)
        norm = _normalize_activation(raw, predictions, k, center)
        rows.append(
            {
                "region_name": group,
                "functional_group": group,
                "mean_activation": raw,
                "normalized_score": norm,
            }
        )
    rows.sort(key=lambda r: r["mean_activation"], reverse=True)
    return rows


def compute_scores(
    predictions: np.ndarray,
    atlas: Atlas,
    k: float = 1.0,
    center: float = 0.0,
) -> ScoreReport:
    predictions = np.asarray(predictions, dtype=np.float64)
    if predictions.ndim != 2:
        raise ValueError("predictions must be 2D (n_timesteps, n_vertices)")

    attention = compute_attention_score(predictions, atlas, k, center)
    emotion = compute_emotion_score(predictions, atlas, k, center)
    tv = compute_temporal_variance(predictions, k, center)
    impact = compute_impact_score(attention, emotion, tv)
    regions = compute_region_breakdown(predictions, atlas, k, center)

    att_idx = _combined_group_vertices(atlas, ATTENTION_GROUPS)
    emo_idx = atlas.get_functional_group_vertices("emotional")

    per_timestep: list[dict[str, float]] = []
    n_t = predictions.shape[0]
    for t in range(n_t):
        att_raw = _vertex_mean_at_timestep(predictions, t, att_idx)
        emo_raw = _vertex_mean_at_timestep(predictions, t, emo_idx)
        overall_raw = float(np.mean(predictions[t]))
        per_timestep.append(
            {
                "attention": _normalize_activation(att_raw, predictions, k, center),
                "emotion": _normalize_activation(emo_raw, predictions, k, center),
                "overall": _normalize_activation(overall_raw, predictions, k, center),
            }
        )

    return ScoreReport(
        attention_score=attention,
        emotion_score=emotion,
        impact_score=impact,
        temporal_variance=tv,
        region_breakdown=regions,
        per_timestep_scores=per_timestep,
    )
