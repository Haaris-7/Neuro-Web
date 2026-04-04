"""Vertex activation → colormap values + optional 2D orthographic projections."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from engine.data.colormaps import AVAILABLE_COLORMAPS, get_lut, map_values_to_colors

logger = logging.getLogger(__name__)


def activation_to_vertex_colors(
    activations: np.ndarray,
    colormap: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
) -> np.ndarray:
    """Map per-vertex activation to RGB colors via 256-entry LUT.

    Args:
        activations: 1-D array of shape (n_vertices,).
        colormap: One of viridis, plasma, inferno, magma.
        vmin/vmax: Normalization range; defaults to data min/max.

    Returns:
        Float32 array of shape (n_vertices, 3) with RGB in [0, 1].
    """
    a = np.asarray(activations, dtype=np.float64).ravel()
    return map_values_to_colors(a, colormap=colormap, vmin=vmin, vmax=vmax)


def timestep_vertex_colors(
    predictions: np.ndarray,
    timestep: int,
    colormap: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
) -> np.ndarray:
    """Vertex colors for a single timestep of the prediction array.

    Args:
        predictions: 2-D array (n_timesteps, n_vertices).
        timestep: Which row to colour.
        colormap: Colormap name.
        vmin/vmax: Optional normalisation range (defaults to global min/max
                   across all timesteps for consistent scaling).

    Returns:
        Float32 (n_vertices, 3) RGB array.
    """
    predictions = np.asarray(predictions, dtype=np.float64)
    if predictions.ndim != 2:
        raise ValueError("predictions must be 2-D (n_timesteps, n_vertices)")
    if timestep < 0 or timestep >= predictions.shape[0]:
        raise IndexError(f"timestep {timestep} out of range (0..{predictions.shape[0] - 1})")
    if vmin is None:
        vmin = float(np.min(predictions))
    if vmax is None:
        vmax = float(np.max(predictions))
    return activation_to_vertex_colors(predictions[timestep], colormap, vmin, vmax)


def mean_vertex_colors(
    predictions: np.ndarray,
    colormap: str = "viridis",
) -> np.ndarray:
    """Mean activation across all timesteps → vertex colors.

    Useful for the default 'combined' heatmap view.
    """
    predictions = np.asarray(predictions, dtype=np.float64)
    mean_act = np.mean(predictions, axis=0)
    return activation_to_vertex_colors(mean_act, colormap)


def generate_2d_projections(
    activations: np.ndarray,
    output_dir: str,
    colormap: str = "viridis",
) -> dict[str, str]:
    """Render 2D orthographic PNG projections for no-WebGL fallback.

    Generates lateral, medial, and dorsal views using matplotlib + nilearn.
    Returns dict mapping view name → file path.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from nilearn import datasets, plotting
    except ImportError:
        logger.warning(
            "matplotlib/nilearn not available for 2D projections — skipping"
        )
        return {}

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    fsavg = datasets.fetch_surf_fsaverage(mesh="fsaverage5")
    n_vertices = activations.shape[0]
    half = n_vertices // 2
    lh_data = activations[:half]
    rh_data = activations[half:]

    views = {
        "lateral_left": ("left", "lateral"),
        "medial_left": ("left", "medial"),
        "lateral_right": ("right", "lateral"),
        "dorsal": ("left", "dorsal"),
    }

    paths: dict[str, str] = {}
    for name, (hemi, view) in views.items():
        surf_mesh = fsavg.pial_left if hemi == "left" else fsavg.pial_right
        surf_data = lh_data if hemi == "left" else rh_data
        try:
            fig = plotting.plot_surf(
                surf_mesh,
                surf_map=surf_data,
                hemi=hemi,
                view=view,
                cmap=colormap,
                colorbar=True,
                title=name.replace("_", " ").title(),
            )
            fpath = str(out / f"{name}.png")
            fig.savefig(fpath, dpi=150, bbox_inches="tight")
            plt.close(fig)
            paths[name] = fpath
        except Exception:
            logger.warning("Failed to render %s view", name, exc_info=True)

    return paths
