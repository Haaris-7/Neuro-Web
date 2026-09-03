import asyncio
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import settings
from database import get_db
from engine.report import load_report
from models.job import JobCreate, JobResponse, JobStatus, job_from_row
from pipeline.url_validator import validate_url

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("", response_model=JobResponse)
async def create_job(payload: JobCreate) -> JobResponse:
    try:
        validated = await asyncio.to_thread(validate_url, payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job_id = str(uuid.uuid4())
    now = _utc_now()
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO jobs (id, url, status, failed_stage, error_message,
                              created_at, updated_at, capture_metadata, config)
            VALUES (?, ?, ?, NULL, NULL, ?, ?, NULL, NULL)
            """,
            (job_id, validated, JobStatus.queued.value, now, now),
        )
    return await get_job_by_id(job_id)


@router.get("", response_model=list[JobResponse])
async def list_jobs() -> list[JobResponse]:
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        rows = await cur.fetchall()
    return [job_from_row(r) for r in rows]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_by_id(job_id: str) -> JobResponse:
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_from_row(row)


@router.get("/{job_id}/report")
async def get_job_report(job_id: str) -> dict:
    async with get_db() as db:
        cur = await db.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    if str(row["status"]) != JobStatus.ready.value:
        raise HTTPException(status_code=409, detail=f"Job is not ready (status: {row['status']})")
    report = await asyncio.to_thread(load_report, job_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str) -> None:
    async with get_db() as db:
        cur = await db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    data_root = Path(settings.DATA_DIR).resolve()
    for subdir in ("captures", "predictions", "reports"):
        target = (data_root / subdir / job_id).resolve()
        try:
            target.relative_to(data_root / subdir)
        except ValueError:
            continue
        if target.is_dir():
            await asyncio.to_thread(shutil.rmtree, target, True)
