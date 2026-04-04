import asyncio
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import settings
from database import get_db
from models.job import JobCreate, JobResponse, JobStatus
from pipeline.url_validator import validate_url

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


async def _row_to_response(row) -> JobResponse:
    cm = json.loads(row["capture_metadata"]) if row["capture_metadata"] else None
    cfg = json.loads(row["config"]) if row["config"] else None
    return JobResponse(
        id=str(row["id"]),
        url=str(row["url"]),
        status=JobStatus(str(row["status"])),
        failed_stage=row["failed_stage"],
        error_message=row["error_message"],
        created_at=_parse_dt(str(row["created_at"])),
        updated_at=_parse_dt(str(row["updated_at"])),
        capture_metadata=cm,
        config=cfg,
    )


@router.post("", response_model=JobResponse)
async def create_job(payload: JobCreate) -> JobResponse:
    try:
        validated = await asyncio.to_thread(validate_url, payload.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    job_id = str(uuid.uuid4())
    now = _utc_now()
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO jobs (
                id, url, status, failed_stage, error_message,
                created_at, updated_at, capture_metadata, config
            ) VALUES (?, ?, ?, NULL, NULL, ?, ?, NULL, NULL)
            """,
            (job_id, validated, JobStatus.queued.value, now, now),
        )
    return await get_job_by_id(job_id)


@router.get("", response_model=list[JobResponse])
async def list_jobs() -> list[JobResponse]:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC",
        )
        rows = await cur.fetchall()
    return [await _row_to_response(r) for r in rows]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_by_id(job_id: str) -> JobResponse:
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return await _row_to_response(row)


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str) -> None:
    async with get_db() as db:
        cur = await db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        await db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    data_root = Path(settings.DATA_DIR).resolve()
    cap = (data_root / "captures" / job_id).resolve()
    try:
        cap.relative_to(data_root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path") from None
    if cap.exists():
        shutil.rmtree(cap, ignore_errors=True)
