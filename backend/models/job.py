import json
from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from fastapi import Path
from pydantic import BaseModel

UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

# Job ids are server-issued UUID4s; rejecting anything else at the router keeps
# path traversal out of every filesystem lookup keyed by job id.
JobId = Annotated[str, Path(pattern=UUID_PATTERN)]


class JobStatus(str, Enum):
    queued = "queued"
    validating = "validating"
    capturing = "capturing"
    analyzing = "analyzing"
    scoring = "scoring"
    ready = "ready"
    failed = "failed"


ACTIVE_STATUSES = (
    JobStatus.validating,
    JobStatus.capturing,
    JobStatus.analyzing,
    JobStatus.scoring,
)


class JobCreate(BaseModel):
    url: str


class JobResponse(BaseModel):
    id: str
    url: str
    status: JobStatus
    failed_stage: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    capture_metadata: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


def _parse_dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def job_from_row(row: Any) -> JobResponse:
    return JobResponse(
        id=str(row["id"]),
        url=str(row["url"]),
        status=JobStatus(str(row["status"])),
        failed_stage=row["failed_stage"],
        error_message=row["error_message"],
        created_at=_parse_dt(str(row["created_at"])),
        updated_at=_parse_dt(str(row["updated_at"])),
        capture_metadata=json.loads(row["capture_metadata"]) if row["capture_metadata"] else None,
        config=json.loads(row["config"]) if row["config"] else None,
    )
