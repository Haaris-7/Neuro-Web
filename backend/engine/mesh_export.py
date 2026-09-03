"""Export the fsaverage5 pial surface as a GLB for the browser heatmap.

Vertex order in each hemisphere node matches the fsaverage5 ordering used by
TRIBE v2 predictions and the atlas, so per-vertex data can be applied directly.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np

from config import settings

logger = logging.getLogger(__name__)

HEMISPHERE_GAP_MM = 4.0
NODE_NAMES = {"left": "left_hemisphere", "right": "right_hemisphere"}

_lock = threading.Lock()


def _load_gifti_geometry(path: str) -> tuple[np.ndarray, np.ndarray]:
    import nibabel as nib
    from nibabel.nifti1 import intent_codes

    img = nib.load(path)
    coords = faces = None
    for darray in img.darrays:
        if darray.intent == intent_codes.code["NIFTI_INTENT_POINTSET"]:
            coords = np.asarray(darray.data, dtype=np.float64)
        elif darray.intent == intent_codes.code["NIFTI_INTENT_TRIANGLE"]:
            faces = np.asarray(darray.data, dtype=np.int64)
    if coords is None or faces is None:
        raise ValueError(f"GIFTI mesh missing pointset or triangles: {path}")
    return coords, faces


def load_fsaverage5_surfaces(
    surface: str = "pial",
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    from nilearn.datasets import fetch_surf_fsaverage

    fs = fetch_surf_fsaverage(mesh="fsaverage5")
    return {
        "left": _load_gifti_geometry(fs[f"{surface}_left"]),
        "right": _load_gifti_geometry(fs[f"{surface}_right"]),
    }


def mesh_path(cache_dir: str | None = None) -> Path:
    root = Path(cache_dir if cache_dir is not None else settings.MODEL_CACHE_DIR).resolve()
    return root / "mesh" / "fsaverage5_pial.glb"


def ensure_brain_mesh(cache_dir: str | None = None) -> Path:
    """Build the GLB on first use and return its path."""
    out = mesh_path(cache_dir)
    with _lock:
        if out.is_file():
            return out
        try:
            import trimesh
        except ImportError as exc:
            raise ImportError("trimesh is required to export the brain mesh") from exc

        surfaces = load_fsaverage5_surfaces()
        (lh_vertices, lh_faces) = surfaces["left"]
        (rh_vertices, rh_faces) = surfaces["right"]
        shift = HEMISPHERE_GAP_MM / 2.0
        lh_shifted = lh_vertices.copy()
        rh_shifted = rh_vertices.copy()
        lh_shifted[:, 0] -= shift
        rh_shifted[:, 0] += shift

        scene = trimesh.Scene()
        for name, vertices, faces in (
            (NODE_NAMES["left"], lh_shifted, lh_faces),
            (NODE_NAMES["right"], rh_shifted, rh_faces),
        ):
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
            scene.add_geometry(mesh, node_name=name, geom_name=name)

        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".tmp.glb")
        scene.export(str(tmp), file_type="glb")
        tmp.replace(out)
        logger.info(
            "Exported fsaverage5 mesh (%d + %d vertices) to %s",
            len(lh_vertices),
            len(rh_vertices),
            out,
        )
        return out
