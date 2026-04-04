import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from database import get_db
from models.job import JobResponse, JobStatus

router = APIRouter(prefix="/jobs", tags=["stream"])


def _parse_dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


async def _fetch_job_row(job_id: str):
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        return await cur.fetchone()


def _row_to_response(row) -> JobResponse:
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


@router.get("/{job_id}/stream")
async def stream_job(job_id: str, request: Request) -> EventSourceResponse:
    initial = await _fetch_job_row(job_id)
    if not initial:
        raise HTTPException(status_code=404, detail="Job not found")
    last_raw = request.headers.get("last-event-id")
    if last_raw is None:
        last_raw = request.headers.get("Last-Event-ID")
    last_id = 0
    if last_raw is not None and str(last_raw).isdigit():
        last_id = int(str(last_raw))
    next_event_id = last_id + 1

    async def publisher():
        nonlocal next_event_id
        while True:
            row = await _fetch_job_row(job_id)
            if not row:
                payload = json.dumps({"error": "job not found"})
                yield {
                    "event": "job",
                    "data": payload,
                    "id": str(next_event_id),
                }
                next_event_id += 1
                break
            job = _row_to_response(row)
            body = job.model_dump(mode="json")
            yield {
                "event": "job",
                "data": json.dumps(body),
                "id": str(next_event_id),
            }
            next_event_id += 1
            if job.status in (JobStatus.ready, JobStatus.failed):
                break
            await asyncio.sleep(1)

    return EventSourceResponse(publisher())
