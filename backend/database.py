from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from config import settings

DB_PATH = Path(settings.DATA_DIR).resolve() / "neuro_web.db"


async def init_db() -> None:
    Path(settings.DATA_DIR).resolve().mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
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
        await db.commit()


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        db.row_factory = aiosqlite.Row
        yield db
        await db.commit()


async def reconcile_stale_jobs() -> None:
    stale = (
        "validating",
        "capturing",
        "analyzing",
        "scoring",
        "enhancing",
        "running",
    )
    placeholders = ",".join("?" * len(stale))
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        await db.execute(
            f"""
            UPDATE jobs
            SET status = 'failed',
                error_message = 'interrupted',
                failed_stage = status,
                updated_at = ?
            WHERE status IN ({placeholders})
            """,
            (now, *stale),
        )
