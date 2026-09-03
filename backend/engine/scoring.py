"""Deterministic 0-10 scores derived from TRIBE v2 vertex predictions.

Predictions are z-scored fMRI-like responses. A network's raw activation is
placed on a 0-10 scale by comparing it with the distribution of activation
across all cortical regions of the same capture, so a score of 5 means "typical
for this page" and the tails mark networks that stand out.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from engine.atlas import Atlas

FUNCTIONAL_GROUPS = ("visual", "attention", "emotional", "language", "default_mode")
ATTENTION_GROUPS = ("visual", "attention")
EMOTION_GROUPS = ("emotional",)
SIGMOID_GAIN = 1.2
EPS = 1e-9


@dataclass
class ScoreReport:
    attention_score: float
    emotion_score: float
    impact_score: float
    temporal_variance: float
    network_breakdown: list[dict[str, Any]]
    region_breakdown: list[dict[str, Any]]
    per_timestep_scores: list[dict[str, float]]


class ActivationContext:
    """Pre-computed region statistics shared by scoring, timeline and overlay."""

    def __init__(self, predictions: np.ndarray, atlas: Atlas) -> None:
        predictions = np.asarray(predictions, dtype=np.float64)
        if predictions.ndim != 2:
            raise ValueError("predictions must be 2D (n_timesteps, n_vertices)")
        if predictions.shape[1] != atlas.n_vertices:
            raise ValueError(
                f"predictions have {predictions.shape[1]} vertices, atlas has {atlas.n_vertices}"
            )
        self.predictions = predictions
        self.atlas = atlas
        self.n_timesteps = predictions.shape[0]
        self.regions = atlas.cortical_regions
        self.region_vertices = {r: atlas.get_region_vertices(r) for r in self.regions}
        self.group_vertices = {
            g: atlas.get_functional_group_vertices(g) for g in FUNCTIONAL_GROUPS
        }
        self.cortical_idx = np.flatnonzero(atlas.cortical_mask())

        self.region_series = np.stack(
            [predictions[:, idx].mean(axis=1) for idx in self.region_vertices.values()],
            axis=1,
        )
        self.region_means = self.region_series.mean(axis=0)
        self.ref_mean = float(self.region_means.mean())
        self.ref_std = float(self.region_means.std()) + EPS
        self.pooled_mean = float(self.region_series.mean())
        self.pooled_std = float(self.region_series.std()) + EPS

    def vertices_for(self, groups: tuple[str, ...]) -> np.ndarray:
        parts = [self.group_vertices[g] for g in groups if self.group_vertices[g].size]
        if not parts:
            return np.array([], dtype=np.int64)
        return np.unique(np.concatenate(parts))

    def raw_mean(self, idx: np.ndarray) -> float:
        if idx.size == 0:
            return self.ref_mean
        return float(self.predictions[:, idx].mean())

    def raw_mean_at(self, t: int, idx: np.ndarray) -> float:
        if idx.size == 0:
            return self.pooled_mean
        return float(self.predictions[t, idx].mean())

    def score(self, raw: float) -> float:
        return _sigmoid_score((raw - self.ref_mean) / self.ref_std)

    def score_at(self, raw: float) -> float:
        return _sigmoid_score((raw - self.pooled_mean) / self.pooled_std)

    def overall_series(self) -> np.ndarray:
        return self.predictions[:, self.cortical_idx].mean(axis=1)

    def temporal_variance_ratio(self) -> float:
        """How much regions fluctuate over the scroll relative to how much they differ.

        Both terms are computed on the same region-level series, so the ratio is
        not damped by averaging over vertices: 1.0 means the typical region moves
        over time as much as regions differ from one another.
        """
        if self.n_timesteps < 2:
            return 0.0
        temporal = float(self.region_series.var(axis=0).mean())
        spatial = float(self.region_means.var()) + EPS
        return temporal / spatial

    def temporal_variance_score(self) -> float:
        ratio = self.temporal_variance_ratio()
        return float(np.clip(10.0 * ratio / (1.0 + ratio), 0.0, 10.0))


def _sigmoid_score(z: float, gain: float = SIGMOID_GAIN) -> float:
    return float(np.clip(10.0 / (1.0 + np.exp(-gain * z)), 0.0, 10.0))


def compute_impact_score(attention: float, emotion: float, temporal_variance: float) -> float:
    return float(np.clip(0.4 * attention + 0.4 * emotion + 0.2 * temporal_variance, 0.0, 10.0))


def compute_scores(predictions: np.ndarray, atlas: Atlas) -> ScoreReport:
    ctx = ActivationContext(predictions, atlas)
    return compute_scores_from_context(ctx)


def compute_scores_from_context(ctx: ActivationContext) -> ScoreReport:
    att_idx = ctx.vertices_for(ATTENTION_GROUPS)
    emo_idx = ctx.vertices_for(EMOTION_GROUPS)
    attention = ctx.score(ctx.raw_mean(att_idx))
    emotion = ctx.score(ctx.raw_mean(emo_idx))
    temporal_variance = ctx.temporal_variance_score()
    impact = compute_impact_score(attention, emotion, temporal_variance)

    network_rows = []
    for group in FUNCTIONAL_GROUPS:
        raw = ctx.raw_mean(ctx.group_vertices[group])
        network_rows.append(
            {
                "network": group,
                "regions": ctx.atlas.functional_groups[group],
                "n_vertices": int(ctx.group_vertices[group].size),
                "mean_activation": raw,
                "normalized_score": ctx.score(raw),
            }
        )
    network_rows.sort(key=lambda r: r["normalized_score"], reverse=True)

    region_rows = []
    for region, raw in zip(ctx.regions, ctx.region_means):
        region_rows.append(
            {
                "region_name": region,
                "functional_group": ctx.atlas.group_of_region(region),
                "n_vertices": int(ctx.region_vertices[region].size),
                "mean_activation": float(raw),
                "normalized_score": ctx.score(float(raw)),
            }
        )
    region_rows.sort(key=lambda r: r["normalized_score"], reverse=True)

    per_timestep = []
    overall = ctx.overall_series()
    for t in range(ctx.n_timesteps):
        per_timestep.append(
            {
                "attention": ctx.score_at(ctx.raw_mean_at(t, att_idx)),
                "emotion": ctx.score_at(ctx.raw_mean_at(t, emo_idx)),
                "overall": ctx.score_at(float(overall[t])),
            }
        )

    return ScoreReport(
        attention_score=attention,
        emotion_score=emotion,
        impact_score=impact,
        temporal_variance=temporal_variance,
        network_breakdown=network_rows,
        region_breakdown=region_rows,
        per_timestep_scores=per_timestep,
    )
