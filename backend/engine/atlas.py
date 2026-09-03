"""Desikan-Killiany cortical parcellation on fsaverage5 (10 242 vertices per hemisphere).

TRIBE v2 predicts on the concatenated left||right fsaverage5 mesh, so vertex
labels are stored in that same order. nilearn bundles the fsaverage5 surfaces
but not the aparc annotation, which is fetched once and cached as JSON.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from config import settings

logger = logging.getLogger(__name__)

CACHE_VERSION = 2
VERTICES_PER_HEMI = 10242

_ANNOT_URLS = {
    "lh": "https://osf.io/download/666fa8abd835c438194cea6d/",
    "rh": "https://osf.io/download/666fa9b36b6c8e329304d4c1/",
}

MEDIAL_WALL = ("unknown", "corpuscallosum")

FUNCTIONAL_GROUPS: dict[str, tuple[str, ...]] = {
    "visual": ("pericalcarine", "cuneus", "lateraloccipital", "lingual", "fusiform"),
    "attention": (
        "superiorparietal",
        "inferiorparietal",
        "supramarginal",
        "caudalmiddlefrontal",
        "precentral",
        "frontalpole",
    ),
    "emotional": (
        "insula",
        "rostralanteriorcingulate",
        "caudalanteriorcingulate",
        "medialorbitofrontal",
        "lateralorbitofrontal",
        "parahippocampal",
        "entorhinal",
        "temporalpole",
    ),
    "language": (
        "superiortemporal",
        "middletemporal",
        "bankssts",
        "parsopercularis",
        "parstriangularis",
        "parsorbitalis",
        "transversetemporal",
    ),
    "default_mode": (
        "posteriorcingulate",
        "isthmuscingulate",
        "precuneus",
        "superiorfrontal",
        "rostralmiddlefrontal",
    ),
}

_memo_lock = threading.Lock()
_memo: dict[str, "Atlas"] = {}


class Atlas:
    def __init__(
        self,
        vertex_labels: np.ndarray,
        region_names: list[str],
        *,
        n_vertices_lh: int,
        n_vertices_rh: int,
    ) -> None:
        self.vertex_labels = np.asarray(vertex_labels, dtype=np.uint16)
        self.region_names = list(region_names)
        self.n_vertices_lh = int(n_vertices_lh)
        self.n_vertices_rh = int(n_vertices_rh)
        self.functional_groups = {
            group: [r for r in regions if r in self.region_names]
            for group, regions in FUNCTIONAL_GROUPS.items()
        }
        self._group_of_region = {
            region: group for group, regions in self.functional_groups.items() for region in regions
        }

    @property
    def n_vertices(self) -> int:
        return int(self.vertex_labels.shape[0])

    @property
    def cortical_regions(self) -> list[str]:
        return [r for r in self.region_names if r not in MEDIAL_WALL]

    def region_of_vertex(self, vertex_idx: int) -> str:
        return self.region_names[int(self.vertex_labels[vertex_idx])]

    def group_of_region(self, region_name: str) -> str | None:
        return self._group_of_region.get(region_name)

    def get_region_vertices(self, region_name: str) -> np.ndarray:
        try:
            code = self.region_names.index(region_name)
        except ValueError as exc:
            raise KeyError(f"Unknown region: {region_name!r}") from exc
        return np.flatnonzero(self.vertex_labels == code)

    def get_functional_group_vertices(self, group_name: str) -> np.ndarray:
        if group_name not in self.functional_groups:
            raise KeyError(
                f"Unknown functional group {group_name!r}; valid: {sorted(self.functional_groups)}"
            )
        parts = [self.get_region_vertices(r) for r in self.functional_groups[group_name]]
        if not parts:
            return np.array([], dtype=np.int64)
        return np.unique(np.concatenate(parts))

    def cortical_mask(self) -> np.ndarray:
        wall_codes = [self.region_names.index(r) for r in MEDIAL_WALL if r in self.region_names]
        return ~np.isin(self.vertex_labels, wall_codes)

    def to_payload(self) -> dict[str, Any]:
        return {
            "version": CACHE_VERSION,
            "atlas": "desikan_killiany",
            "mesh": "fsaverage5",
            "n_vertices_lh": self.n_vertices_lh,
            "n_vertices_rh": self.n_vertices_rh,
            "region_names": self.region_names,
            "vertex_labels": self.vertex_labels.tolist(),
            "functional_groups": self.functional_groups,
            "medial_wall": list(MEDIAL_WALL),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Atlas | None:
        if payload.get("version") != CACHE_VERSION:
            return None
        names = payload.get("region_names")
        labels = payload.get("vertex_labels")
        n_lh = payload.get("n_vertices_lh")
        n_rh = payload.get("n_vertices_rh")
        if not names or not labels or not n_lh or not n_rh or len(labels) != n_lh + n_rh:
            return None
        return cls(np.asarray(labels), names, n_vertices_lh=n_lh, n_vertices_rh=n_rh)


def _cache_path(cache_dir: Path) -> Path:
    return cache_dir / "atlas" / "desikan_killiany_fsaverage5.json"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "NeuroWeb/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to download atlas annotation from {url}: {exc}") from exc
    tmp = dest.with_suffix(".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dest)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _build_from_annotations(cache_dir: Path) -> Atlas:
    try:
        from nibabel.freesurfer import read_annot
    except ImportError as exc:
        raise ImportError("nibabel is required to read FreeSurfer annotations") from exc

    staging = cache_dir / "atlas" / "fsaverage5_label"
    labels_by_hemi: dict[str, np.ndarray] = {}
    names_by_hemi: dict[str, list[str]] = {}
    for hemi, url in _ANNOT_URLS.items():
        path = staging / f"{hemi}.aparc.annot"
        if not path.is_file():
            logger.info("Downloading %s Desikan-Killiany annotation", hemi)
            _download(url, path)
        labels, _, names = read_annot(str(path))
        if labels.shape[0] != VERTICES_PER_HEMI:
            raise ValueError(
                f"{path} has {labels.shape[0]} vertices, expected {VERTICES_PER_HEMI} (fsaverage5)"
            )
        labels_by_hemi[hemi] = np.asarray(labels, dtype=np.int64)
        names_by_hemi[hemi] = [n.decode("utf-8") if isinstance(n, bytes) else str(n) for n in names]

    if names_by_hemi["lh"] != names_by_hemi["rh"]:
        raise ValueError("Left and right annotation color tables differ")
    region_names = names_by_hemi["lh"]
    combined = np.concatenate([labels_by_hemi["lh"], labels_by_hemi["rh"]])
    combined[combined < 0] = 0
    if combined.max() >= len(region_names):
        raise ValueError("Annotation label index exceeds color table length")
    return Atlas(
        combined.astype(np.uint16),
        region_names,
        n_vertices_lh=VERTICES_PER_HEMI,
        n_vertices_rh=VERTICES_PER_HEMI,
    )


def load_atlas(cache_dir: str | None = None) -> Atlas:
    root = Path(cache_dir if cache_dir is not None else settings.MODEL_CACHE_DIR).expanduser().resolve()
    key = str(root)
    with _memo_lock:
        if key in _memo:
            return _memo[key]
        path = _cache_path(root)
        atlas: Atlas | None = None
        if path.is_file():
            try:
                atlas = Atlas.from_payload(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                atlas = None
        if atlas is None:
            atlas = _build_from_annotations(root)
            _atomic_write_json(path, atlas.to_payload())
        _memo[key] = atlas
        return atlas
