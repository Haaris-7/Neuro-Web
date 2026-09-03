import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from database import get_db
from models.job import JobStatus, job_from_row

router = APIRouter(prefix="/jobs", tags=["stream"])

POLL_INTERVAL_S = 1.0


async def _fetch_job_row(job_id: str):
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        return await cur.fetchone()


@router.get("/{job_id}/stream")
async def stream_job(job_id: str, request: Request) -> EventSourceResponse:
    if not await _fetch_job_row(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    last_raw = request.headers.get("last-event-id", "")
    next_event_id = int(last_raw) + 1 if last_raw.isdigit() else 1

    async def publisher():
        nonlocal next_event_id
        while not await request.is_disconnected():
            row = await _fetch_job_row(job_id)
            if not row:
                yield {"event": "job", "data": json.dumps({"error": "job not found"}), "id": str(next_event_id)}
                return
            job = job_from_row(row)
            yield {"event": "job", "data": json.dumps(job.model_dump(mode="json")), "id": str(next_event_id)}
            next_event_id += 1
            if job.status in (JobStatus.ready, JobStatus.failed):
                return
            await asyncio.sleep(POLL_INTERVAL_S)

    return EventSourceResponse(publisher())
