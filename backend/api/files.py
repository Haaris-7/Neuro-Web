from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import settings
from models.job import JobId

router = APIRouter(prefix="/jobs", tags=["files"])

_ARTIFACT_DIRS = ("captures", "reports", "predictions")
_MEDIA_TYPES = {
    ".png": "image/png",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".json": "application/json",
    ".txt": "text/plain; charset=utf-8",
    ".u8": "application/octet-stream",
    ".npz": "application/octet-stream",
}


def resolve_artifact(job_id: str, relative_path: str) -> Path:
    """Locate a job artifact, refusing anything outside the job's own directories."""
    if not relative_path or Path(relative_path).is_absolute():
        raise HTTPException(status_code=404, detail="File not found")
    suffix = Path(relative_path).suffix.lower()
    if suffix not in _MEDIA_TYPES:
        raise HTTPException(status_code=404, detail="File not found")
    data_root = Path(settings.DATA_DIR).resolve()
    for subdir in _ARTIFACT_DIRS:
        job_dir = data_root / subdir / job_id
        candidate = (job_dir / relative_path).resolve()
        try:
            candidate.relative_to(job_dir)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/{job_id}/files/{relative_path:path}")
async def get_job_file(job_id: JobId, relative_path: str) -> FileResponse:
    path = resolve_artifact(job_id, relative_path)
    return FileResponse(
        str(path),
        media_type=_MEDIA_TYPES[path.suffix.lower()],
        headers={"Cache-Control": "private, max-age=3600"},
    )
