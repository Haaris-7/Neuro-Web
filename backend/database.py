from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from config import settings
from models.job import ACTIVE_STATUSES, JobStatus


def db_path() -> Path:
    return Path(settings.DATA_DIR).resolve() / "neuro_web.db"


async def init_db() -> None:
    db_path().parent.mkdir(parents=True, exist_ok=True)
    async with get_db() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                status TEXT NOT NULL,
                failed_stage TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                capture_metadata TEXT,
                config TEXT
            )
            """
        )


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(str(db_path())) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        db.row_factory = aiosqlite.Row
        yield db
        await db.commit()


async def reconcile_stale_jobs() -> None:
    """Mark jobs that were mid-pipeline when the server stopped as failed."""
    stale = [s.value for s in ACTIVE_STATUSES]
    placeholders = ",".join("?" * len(stale))
    async with get_db() as db:
        await db.execute(
            f"""
            UPDATE jobs
            SET status = ?, error_message = 'Interrupted by a server restart', failed_stage = status, updated_at = ?
            WHERE status IN ({placeholders})
            """,
            (JobStatus.failed.value, datetime.now(timezone.utc).isoformat(), *stale),
        )
