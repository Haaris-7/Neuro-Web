"""Per-vertex activation maps for the 3D heatmap and 2D fallback renders."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from engine.atlas import Atlas

logger = logging.getLogger(__name__)

VERTEX_ACTIVATION_FILE = "vertex_activation.u8"
VERTEX_ACTIVATION_META_FILE = "vertex_activation.json"
PERCENTILE_RANGE = (2.0, 98.0)


def normalize_vertex_map(values: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    span = max(vmax - vmin, 1e-9)
    return np.clip((values - vmin) / span, 0.0, 1.0)


def export_vertex_activation(
    predictions: np.ndarray, atlas: Atlas, output_dir: Path
) -> dict[str, str | int | float]:
    """Write mean and per-timestep vertex activation as uint8 in [0, 255].

    Layout: the first row is the time-averaged map, followed by one row per
    timestep. Medial wall vertices are forced to zero so they render as
    background. A JSON sidecar describes the shape and the value range used.
    """
    predictions = np.asarray(predictions, dtype=np.float64)
    mask = atlas.cortical_mask()
    mean_map = predictions.mean(axis=0)
    vmin, vmax = np.percentile(predictions[:, mask], PERCENTILE_RANGE)
    frames = np.concatenate([mean_map[None, :], predictions], axis=0)
    normalized = normalize_vertex_map(frames, float(vmin), float(vmax))
    normalized[:, ~mask] = 0.0
    quantized = np.rint(normalized * 255.0).astype(np.uint8)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / VERTEX_ACTIVATION_FILE).write_bytes(quantized.tobytes(order="C"))
    meta = {
        "file": VERTEX_ACTIVATION_FILE,
        "dtype": "uint8",
        "n_vertices": int(predictions.shape[1]),
        "n_timesteps": int(predictions.shape[0]),
        "layout": "row 0 = time-averaged map, rows 1..n_timesteps = per-timestep maps",
        "vmin": float(vmin),
        "vmax": float(vmax),
    }
    (output_dir / VERTEX_ACTIVATION_META_FILE).write_text(json.dumps(meta, indent=2))
    return meta


def generate_2d_projections(
    activations: np.ndarray,
    output_dir: Path,
    colormap: str = "viridis",
) -> dict[str, str]:
    """Render static lateral/medial/dorsal views for clients without WebGL.

    Returns view name -> path relative to ``output_dir``'s parent.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from nilearn import datasets, plotting
    except ImportError:
        logger.warning("matplotlib/nilearn unavailable; skipping 2D projections")
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)
    fsaverage = datasets.fetch_surf_fsaverage(mesh="fsaverage5")
    half = activations.shape[0] // 2
    hemi_data = {"left": activations[:half], "right": activations[half:]}
    vmin, vmax = np.percentile(activations, PERCENTILE_RANGE)

    views = {
        "lateral_left": ("left", "lateral"),
        "medial_left": ("left", "medial"),
        "lateral_right": ("right", "lateral"),
        "medial_right": ("right", "medial"),
        "dorsal": ("left", "dorsal"),
    }
    paths: dict[str, str] = {}
    for name, (hemi, view) in views.items():
        try:
            fig = plotting.plot_surf(
                fsaverage[f"pial_{hemi}"],
                surf_map=hemi_data[hemi],
                bg_map=fsaverage[f"sulc_{hemi}"],
                hemi=hemi,
                view=view,
                cmap=colormap,
                vmin=float(vmin),
                vmax=float(vmax),
                colorbar=True,
                title=name.replace("_", " ").title(),
            )
            target = output_dir / f"{name}.png"
            fig.savefig(str(target), dpi=120, bbox_inches="tight", facecolor="#060a14")
            plt.close(fig)
            paths[name] = f"{output_dir.name}/{target.name}"
        except Exception:
            logger.warning("Failed to render %s projection", name, exc_info=True)
    return paths
