import asyncio
import json
import uuid
from datetime import datetime, timezone

from config import settings
from database import get_db
from models.job import JobStatus
from pipeline.capture import capture_website
from pipeline.url_validator import validate_url


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _update_job(
    job_id: str,
    status: JobStatus,
    failed_stage: str | None = None,
    error_message: str | None = None,
    capture_metadata: dict | None = None,
) -> None:
    now = _utc_now()
    async with get_db() as db:
        if capture_metadata is not None:
            await db.execute(
                """
                UPDATE jobs
                SET status = ?, failed_stage = ?, error_message = ?,
                    capture_metadata = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status.value,
                    failed_stage,
                    error_message,
                    json.dumps(capture_metadata),
                    now,
                    job_id,
                ),
            )
        else:
            await db.execute(
                """
                UPDATE jobs
                SET status = ?, failed_stage = ?, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.value, failed_stage, error_message, now, job_id),
            )


async def _fetch_next_queued() -> str | None:
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT id FROM jobs
            WHERE status = ?
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (JobStatus.queued.value,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return str(row["id"])


async def _get_job_url(job_id: str) -> str | None:
    async with get_db() as db:
        cur = await db.execute("SELECT url FROM jobs WHERE id = ?", (job_id,))
        row = await cur.fetchone()
        if not row:
            return None
        return str(row["url"])


async def _process_job(job_id: str) -> None:
    url_row = await _get_job_url(job_id)
    if url_row is None:
        return
    url = url_row
    try:
        await _update_job(job_id, JobStatus.validating, None, None)
        validated = await asyncio.to_thread(validate_url, url)
        await _update_job(job_id, JobStatus.capturing, None, None)
        cap_cfg = {
            "data_dir": settings.DATA_DIR,
            "viewport_w": settings.CAPTURE_VIEWPORT_W,
            "viewport_h": settings.CAPTURE_VIEWPORT_H,
            "capture_duration": settings.CAPTURE_DURATION,
            "navigation_timeout_ms": max(settings.CAPTURE_DURATION * 1000, 60000),
            "default_timeout_ms": 30000,
            "max_redirects": settings.MAX_REDIRECTS,
            "max_video_size_mb": settings.MAX_VIDEO_SIZE_MB,
        }
        artifacts = await capture_website(job_id, validated, cap_cfg)
        await _update_job(
            job_id,
            JobStatus.ready,
            None,
            None,
            capture_metadata=artifacts,
        )
    except Exception as e:
        stage = JobStatus.validating
        async with get_db() as db:
            cur = await db.execute(
                "SELECT status FROM jobs WHERE id = ?",
                (job_id,),
            )
            row = await cur.fetchone()
            if row:
                try:
                    stage = JobStatus(str(row["status"]))
                except ValueError:
                    stage = JobStatus.validating
        await _update_job(
            job_id,
            JobStatus.failed,
            failed_stage=stage.value,
            error_message=str(e),
        )


async def worker_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        job_id = await _fetch_next_queued()
        if job_id is None:
            try:
                await asyncio.wait_for(stop.wait(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            continue
        await _process_job(job_id)
