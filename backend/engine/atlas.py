"""Desikan–Killiany cortical atlas on fsaverage5 (10242 vertices / hemisphere)."""

from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from config import settings

_CACHE_VERSION = 1

# OSF-hosted fsaverage5 label files (Desikan–Killiany aparc), not shipped with nilearn.
_ANNOT_URLS = {
    "lh": "https://osf.io/download/666fa8abd835c438194cea6d/",
    "rh": "https://osf.io/download/666fa9b36b6c8e329304d4c1/",
}

_atlas_memo: tuple[str, "Atlas"] | None = None


def _require_nilearn_nibabel() -> tuple[Any, Any]:
    try:
        from nibabel.freesurfer import read_annot
    except ImportError as exc:
        raise ImportError(
            "The atlas module requires nibabel (FreeSurfer annotation I/O). "
            "Install with: pip install nibabel"
        ) from exc
    try:
        from nilearn.datasets import fetch_surf_fsaverage
    except ImportError as exc:
        raise ImportError(
            "The atlas module requires nilearn (fsaverage surface templates). "
            "Install with: pip install nilearn"
        ) from exc
    return fetch_surf_fsaverage, read_annot


def _json_cache_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "desikan_killiany_fsaverage5.json"


def _annot_staging_dir(data_dir: Path) -> Path:
    p = data_dir / "neuro_web_atlas" / "fsaverage5_label"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "NeuroWeb-Atlas/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to download atlas annotation data from {url!r}: {exc}") from exc
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dest)


def _ensure_annotation_files(data_dir: Path, read_annot: Any) -> tuple[Path, Path]:
    staging = _annot_staging_dir(data_dir)
    lh_path = staging / "lh.aparc.annot"
    rh_path = staging / "rh.aparc.annot"
    if not lh_path.is_file() or not rh_path.is_file():
        _download_file(_ANNOT_URLS["lh"], lh_path)
        _download_file(_ANNOT_URLS["rh"], rh_path)
    for p in (lh_path, rh_path):
        labels, _, _ = read_annot(str(p))
        if labels.shape[0] != 10242:
            raise ValueError(
                f"Expected 10242 vertices in {p}, found {labels.shape[0]} — wrong fsaverage resolution?"
            )
    return lh_path, rh_path


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2)
    fd, tmp = tempfile.mkstemp(suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


_FG_VISUAL = [
    "pericalcarine",
    "cuneus",
    "lateraloccipital",
    "fusiform",
    "lingual",
]
_FG_ATTENTION = [
    "rostralmiddlefrontal",
    "caudalmiddlefrontal",
    "superiorparietal",
    "frontalpole",
    "precentral",
]
_FG_EMOTIONAL = [
    "insula",
    "rostralanteriorcingulate",
    "caudalanteriorcingulate",
    "medialorbitofrontal",
    "lateralorbitofrontal",
]
_FG_LANGUAGE = [
    "superiortemporal",
    "parsopercularis",
    "parstriangularis",
    "transversetemporal",
]
_FG_DEFAULT_MODE = [
    "medialorbitofrontal",
    "isthmuscingulate",
    "posteriorcingulate",
    "precuneus",
    "inferiorparietal",
    "superiorfrontal",
]


class Atlas:
    """Vertex-level Desikan–Killiany labels on concatenated lh||rh fsaverage5 meshes."""

    FUNCTIONAL_GROUPS: dict[str, list[str]] = {
        "visual_processing": list(_FG_VISUAL),
        "visual": list(_FG_VISUAL),
        "attention_network": list(_FG_ATTENTION),
        "attention": list(_FG_ATTENTION),
        "emotional_processing": list(_FG_EMOTIONAL),
        "emotional": list(_FG_EMOTIONAL),
        "language": list(_FG_LANGUAGE),
        "default_mode": list(_FG_DEFAULT_MODE),
    }

    def __init__(
        self,
        vertex_labels: np.ndarray,
        region_names: list[str],
        *,
        functional_groups: dict[str, list[str]] | None = None,
        n_vertices_lh: int | None = None,
        n_vertices_rh: int | None = None,
    ) -> None:
        if vertex_labels.dtype != np.uint16:
            vertex_labels = np.asarray(vertex_labels, dtype=np.uint16)
        self.vertex_labels = vertex_labels
        self.region_names = list(region_names)
        half = len(vertex_labels) // 2
        self.n_vertices_lh = int(n_vertices_lh if n_vertices_lh is not None else half)
        self.n_vertices_rh = int(n_vertices_rh if n_vertices_rh is not None else half)
        self.functional_groups = (
            {k: list(v) for k, v in functional_groups.items()}
            if functional_groups is not None
            else {k: list(v) for k, v in self.FUNCTIONAL_GROUPS.items()}
        )

    @property
    def n_vertices(self) -> int:
        return int(self.vertex_labels.shape[0])

    def get_region_name(self, vertex_idx: int) -> str:
        if vertex_idx < 0 or vertex_idx >= self.n_vertices:
            raise IndexError(f"vertex_idx out of range: {vertex_idx} (n_vertices={self.n_vertices})")
        code = int(self.vertex_labels[vertex_idx])
        if code >= len(self.region_names):
            raise IndexError(f"Label index {code} has no region_names entry")
        return self.region_names[code]

    def get_region_vertices(self, region_name: str) -> np.ndarray:
        try:
            idx = self.region_names.index(region_name)
        except ValueError as exc:
            raise KeyError(f"Unknown region name: {region_name!r}") from exc
        return np.flatnonzero(self.vertex_labels == idx).astype(np.int64, copy=False)

    def get_functional_group(self, group_name: str) -> list[str]:
        if group_name not in self.functional_groups:
            raise KeyError(
                f"Unknown functional group: {group_name!r}. "
                f"Valid keys: {sorted(self.functional_groups)}"
            )
        known = set(self.region_names)
        return [n for n in self.functional_groups[group_name] if n in known]

    def get_functional_group_vertices(self, group_name: str) -> np.ndarray:
        regions = self.get_functional_group(group_name)
        if not regions:
            return np.array([], dtype=np.int64)
        parts = [self.get_region_vertices(r) for r in regions]
        return np.unique(np.concatenate(parts)).astype(np.int64, copy=False)


def _payload_from_atlas(atlas: Atlas) -> dict[str, Any]:
    n_lh = atlas.n_vertices_lh
    n_rh = atlas.n_vertices_rh
    return {
        "version": _CACHE_VERSION,
        "n_vertices_lh": n_lh,
        "n_vertices_rh": n_rh,
        "region_names": list(atlas.region_names),
        "vertex_labels": [int(x) for x in atlas.vertex_labels.tolist()],
        "functional_groups": {k: list(v) for k, v in atlas.functional_groups.items()},
    }


def _build_atlas_from_annots(read_annot: Any, lh_annot: Path, rh_annot: Path) -> Atlas:
    lh_labels, _, lh_names = read_annot(str(lh_annot))
    rh_labels, _, rh_names = read_annot(str(rh_annot))
    lh_names_d = [n.decode("utf-8") if isinstance(n, bytes) else str(n) for n in lh_names]
    rh_names_d = [n.decode("utf-8") if isinstance(n, bytes) else str(n) for n in rh_names]
    if lh_names_d != rh_names_d:
        raise ValueError("Left and right annotation color tables differ; unsupported.")
    region_names = lh_names_d
    lh_idx = np.asarray(lh_labels, dtype=np.int64)
    rh_idx = np.asarray(rh_labels, dtype=np.int64)
    if lh_idx.max() >= len(region_names) or rh_idx.max() >= len(region_names):
        raise ValueError("Annotation label indices exceed color table length.")
    combined = np.concatenate([lh_idx, rh_idx]).astype(np.uint16)
    n_lh, n_rh = lh_idx.shape[0], rh_idx.shape[0]
    return Atlas(
        combined,
        region_names,
        n_vertices_lh=n_lh,
        n_vertices_rh=n_rh,
    )


def _try_load_json_cache(path: Path) -> Atlas | None:
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    if payload.get("version") != _CACHE_VERSION:
        return None
    names = payload.get("region_names")
    verts = payload.get("vertex_labels")
    if not names or not verts:
        return None
    n_lh = int(payload.get("n_vertices_lh", len(verts) // 2))
    n_rh = int(payload.get("n_vertices_rh", len(verts) // 2))
    if len(verts) != n_lh + n_rh:
        return None
    fg = payload.get("functional_groups")
    functional_groups = fg if isinstance(fg, dict) and fg else None
    arr = np.asarray(verts, dtype=np.uint16)
    return Atlas(arr, names, functional_groups=functional_groups, n_vertices_lh=n_lh, n_vertices_rh=n_rh)


def load_atlas(cache_dir: str | None = None) -> Atlas:
    """
    Load the Desikan–Killiany fsaverage5 atlas, using JSON cache when valid.

    On a cache miss, downloads surface templates via nilearn (see
    :func:`nilearn.datasets.fetch_surf_fsaverage`), fetches ``.annot`` label
    files, builds ``vertex_labels``, and refreshes the JSON cache.
    """
    global _atlas_memo
    data_dir = Path(cache_dir if cache_dir is not None else settings.MODEL_CACHE_DIR).expanduser()
    key = str(data_dir.resolve())
    if _atlas_memo is not None and _atlas_memo[0] == key:
        return _atlas_memo[1]

    json_path = _json_cache_path()
    cached = _try_load_json_cache(json_path)
    if cached is not None:
        _atlas_memo = (key, cached)
        return cached

    fetch_surf_fsaverage, read_annot = _require_nilearn_nibabel()
    # Ensures fsaverage5 Gifti surfaces are available under nilearn's data layout.
    fetch_surf_fsaverage(mesh="fsaverage5", data_dir=str(data_dir))

    lh_p, rh_p = _ensure_annotation_files(data_dir, read_annot)
    atlas = _build_atlas_from_annots(read_annot, lh_p, rh_p)
    _atomic_write_json(json_path, _payload_from_atlas(atlas))
    _atlas_memo = (key, atlas)
    return atlas


__all__ = ["Atlas", "load_atlas"]
