from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    import nibabel as nib
    from nibabel.nifti1 import intent_codes
    from nilearn.datasets import fetch_atlas_surf_destrieux, fetch_surf_fsaverage
    from nilearn.surface import load_surf_data
    import trimesh
except ImportError as e:
    _OPTIONAL_IMPORT_ERROR: ImportError | None = e
else:
    _OPTIONAL_IMPORT_ERROR = None

from config import settings


def _ensure_mesh_deps() -> None:
    if _OPTIONAL_IMPORT_ERROR is not None:
        raise ImportError(
            "mesh_export requires nibabel, nilearn, and trimesh. "
            "Install backend requirements (pip install -r backend/requirements.txt)."
        ) from _OPTIONAL_IMPORT_ERROR


def _load_surface_geometry(surface_path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    path = Path(surface_path)
    path_str = str(path)

    try:
        img = nib.load(path_str)
        if isinstance(img, nib.gifti.GiftiImage):
            coords = faces = None
            pt_code = intent_codes.code["NIFTI_INTENT_POINTSET"]
            tri_code = intent_codes.code["NIFTI_INTENT_TRIANGLE"]
            for da in img.darrays:
                if da.intent == pt_code:
                    coords = np.asarray(da.data, dtype=np.float64)
                elif da.intent == tri_code:
                    faces = np.asarray(da.data, dtype=np.int64)
            if coords is None or faces is None:
                raise ValueError(f"GIFTI mesh missing pointset or triangles: {path_str}")
            return coords, faces
    except Exception:
        pass

    try:
        coords, faces = nib.freesurfer.read_geometry(path_str)
        return coords.astype(np.float64), faces.astype(np.int64)
    except Exception as e:
        raise RuntimeError(f"Failed to load surface geometry from {path_str}") from e


def load_fsaverage5_surfaces(
    cache_dir: str | None = None,
) -> tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]:
    _ensure_mesh_deps()
    data_root = Path(cache_dir if cache_dir is not None else settings.MODEL_CACHE_DIR).resolve()
    data_root.mkdir(parents=True, exist_ok=True)
    fs = fetch_surf_fsaverage(mesh="fsaverage5", data_dir=str(data_root))
    lh = _load_surface_geometry(fs.pial_left)
    rh = _load_surface_geometry(fs.pial_right)
    return lh, rh


def _hemisphere_offset_x(
    lh_vertices: np.ndarray, rh_vertices: np.ndarray, gap_mm: float = 5.0
) -> float:
    lh_xmax = float(np.max(lh_vertices[:, 0]))
    rh_xmin = float(np.min(rh_vertices[:, 0]))
    return lh_xmax - rh_xmin + gap_mm


def _build_region_sidecar(data_dir: str) -> dict[str, Any]:
    atlas = fetch_atlas_surf_destrieux(data_dir=data_dir)
    left_ids = np.asarray(load_surf_data(atlas.map_left), dtype=np.int64).tolist()
    right_ids = np.asarray(load_surf_data(atlas.map_right), dtype=np.int64).tolist()
    return {
        "atlas": "destrieux_surface",
        "vertex_index_to_region_id": {
            "left_hemisphere": left_ids,
            "right_hemisphere": right_ids,
        },
        "labels": list(atlas.labels),
    }


def export_brain_mesh(output_path: str, cache_dir: str | None = None) -> str:
    _ensure_mesh_deps()
    out = Path(output_path)
    if out.suffix.lower() != ".glb":
        out = out / "fsaverage5.glb"
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    json_path = out.with_suffix(".json")
    data_dir = str(Path(cache_dir if cache_dir is not None else settings.MODEL_CACHE_DIR).resolve())

    if out.exists():
        if not json_path.exists():
            try:
                sidecar = _build_region_sidecar(data_dir=data_dir)
                json_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
            except Exception:
                pass
        return str(out)

    (lh_vertices, lh_faces), (rh_vertices, rh_faces) = load_fsaverage5_surfaces(cache_dir=cache_dir)

    offset = _hemisphere_offset_x(lh_vertices, rh_vertices)
    rh_shifted = rh_vertices.copy()
    rh_shifted[:, 0] += offset

    lh_mesh = trimesh.Trimesh(vertices=lh_vertices, faces=lh_faces, process=False)
    rh_mesh = trimesh.Trimesh(vertices=rh_shifted, faces=rh_faces, process=False)
    lh_mesh.vertex_normals
    rh_mesh.vertex_normals

    scene = trimesh.Scene()
    scene.add_geometry(lh_mesh, geom_name="left_hemisphere")
    scene.add_geometry(rh_mesh, geom_name="right_hemisphere")
    scene.export(str(out))

    try:
        sidecar = _build_region_sidecar(data_dir)
        json_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    except Exception:
        if json_path.exists():
            json_path.unlink(missing_ok=True)
        if out.exists():
            out.unlink(missing_ok=True)
        raise

    return str(out)
