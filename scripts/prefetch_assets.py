"""Download the fsaverage5 Desikan-Killiany atlas and export the brain mesh.

Run from the backend directory (``make prefetch``) so that the backend
package imports resolve. Both assets are otherwise built lazily on the first
request, which adds latency to the first analysis.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from engine.atlas import load_atlas  # noqa: E402
from engine.mesh_export import ensure_brain_mesh  # noqa: E402


def main() -> None:
    t0 = time.monotonic()
    atlas = load_atlas()
    print(
        f"Atlas ready: {atlas.n_vertices} vertices, {len(atlas.cortical_regions)} cortical regions"
    )
    mesh = ensure_brain_mesh()
    print(f"Mesh ready: {mesh} ({mesh.stat().st_size // 1024} KB)")
    print(f"Done in {time.monotonic() - t0:.1f}s")


if __name__ == "__main__":
    main()
