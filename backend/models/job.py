from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class JobStatus(str, Enum):
    queued = "queued"
    validating = "validating"
    capturing = "capturing"
    analyzing = "analyzing"
    scoring = "scoring"
    enhancing = "enhancing"
    ready = "ready"
    failed = "failed"


class JobCreate(BaseModel):
    url: str


class Job(BaseModel):
    id: str
    url: str
    status: JobStatus
    failed_stage: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    capture_metadata: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


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
