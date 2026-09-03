"""Deterministic stand-in for TRIBE v2 so the pipeline can run without a GPU.

Predictions follow the same contract as the real model: one row per second on
the fsaverage5 mesh (left hemisphere then right, 20 484 vertices). Values are
seeded from the job id and shaped by the capture (scroll speed, on-screen
controls and text density) so downstream scoring exercises realistic structure.
Reports produced this way are labelled ``inference_backend: mock``.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

import numpy as np

from engine.atlas import Atlas

TR_S = 1.0

_NETWORK_BASELINES = {
    "visual": 0.35,
    "attention": 0.2,
    "emotional": 0.05,
    "language": 0.1,
    "default_mode": -0.15,
}


def _seed(job_id: str) -> int:
    return int.from_bytes(hashlib.sha256(job_id.encode()).digest()[:8], "little")


def _viewport_stats(
    t: float,
    scroll_timeline: list[dict[str, float]],
    dom: dict[str, Any],
    viewport_h: float,
) -> tuple[float, float, float]:
    """Scroll speed (px/s), on-screen control count and on-screen word count at time t."""
    if not scroll_timeline:
        return 0.0, 0.0, 0.0
    ms = t * 1000.0
    idx = min(
        range(len(scroll_timeline)),
        key=lambda i: abs(float(scroll_timeline[i]["time_ms"]) - ms),
    )
    top = float(scroll_timeline[idx]["scroll_y"])
    speed = 0.0
    if idx > 0:
        prev = scroll_timeline[idx - 1]
        dt = (float(scroll_timeline[idx]["time_ms"]) - float(prev["time_ms"])) / 1000.0
        if dt > 0:
            speed = abs(top - float(prev["scroll_y"])) / dt
    bottom = top + viewport_h

    def on_screen(item: dict[str, Any]) -> bool:
        y = float(item.get("y", 0.0))
        h = float(item.get("height", 0.0))
        return y < bottom and y + h > top

    controls = sum(1 for r in dom.get("regions", []) if r.get("is_control") and on_screen(r))
    words = sum(
        len(str(b.get("text", "")).split()) for b in dom.get("text_blocks", []) if on_screen(b)
    )
    return speed, float(controls), float(words)


def mock_predict(
    *,
    job_id: str,
    duration_s: float,
    atlas: Atlas,
    scroll_timeline: list[dict[str, float]],
    dom: dict[str, Any],
    viewport_h: float,
) -> tuple[np.ndarray, list[float]]:
    n_t = max(1, int(math.ceil(duration_s / TR_S)))
    n_v = atlas.n_vertices
    rng = np.random.default_rng(_seed(job_id))

    masks = {
        name: np.isin(np.arange(n_v), atlas.get_functional_group_vertices(name))
        for name in _NETWORK_BASELINES
    }
    region_offsets = rng.normal(0.0, 0.12, size=len(atlas.region_names))
    baseline = region_offsets[atlas.vertex_labels.astype(np.int64)]
    for name, level in _NETWORK_BASELINES.items():
        baseline = baseline + level * masks[name]
    vertex_jitter = rng.normal(0.0, 0.05, size=n_v)

    starts: list[float] = []
    rows = []
    for i in range(n_t):
        t = i * TR_S
        starts.append(t)
        speed, controls, words = _viewport_stats(t, scroll_timeline, dom, viewport_h)
        visual_gain = 0.25 * math.tanh(speed / 400.0)
        attention_gain = 0.06 * min(controls, 12)
        language_gain = 0.004 * min(words, 150)
        emotional_gain = 0.15 * math.sin(2 * math.pi * t / max(duration_s, 1.0)) * (controls > 4)
        frame = baseline + vertex_jitter
        frame = frame + visual_gain * masks["visual"]
        frame = frame + attention_gain * masks["attention"]
        frame = frame + language_gain * masks["language"]
        frame = frame + emotional_gain * masks["emotional"]
        frame = frame + rng.normal(0.0, 0.04, size=n_v)
        rows.append(frame.astype(np.float32))

    preds = np.stack(rows)
    if n_t > 2:
        kernel = np.array([0.25, 0.5, 0.25], dtype=np.float32)
        padded = np.concatenate([preds[:1], preds, preds[-1:]], axis=0)
        preds = (
            kernel[0] * padded[:-2] + kernel[1] * padded[1:-1] + kernel[2] * padded[2:]
        ).astype(np.float32)
    return preds, starts
