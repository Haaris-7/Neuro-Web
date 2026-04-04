import asyncio
import json
import logging
from datetime import datetime, timezone

from config import settings
from database import get_db
from models.job import JobStatus
from pipeline.capture import capture_website
from pipeline.url_validator import validate_url

logger = logging.getLogger(__name__)


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


def _run_inference_sync(job_id: str) -> dict:
    """Run TRIBE v2 inference in a thread-safe manner (called via asyncio.to_thread)."""
    from pipeline.inference import run_inference

    return run_inference(job_id)


def _run_scoring_sync(job_id: str, url: str, inference_meta: dict) -> dict:
    """Run deterministic core engine scoring (called via asyncio.to_thread)."""
    import json
    from pathlib import Path

    import numpy as np

    from engine.report import compile_report

    preds_path = Path(inference_meta["combined_preds_path"])
    preds_data = np.load(str(preds_path))
    predictions = preds_data["preds"]

    segment_alignment = inference_meta.get("segment_alignment", [])

    capture_dir = Path(settings.DATA_DIR) / "captures" / job_id

    report = compile_report(
        job_id=job_id,
        url=url,
        predictions=predictions,
        segment_alignment=segment_alignment,
        capture_dir=str(capture_dir),
        viewport_height=settings.CAPTURE_VIEWPORT_H,
    )

    return {
        "attention_score": report.scores.attention_score,
        "emotion_score": report.scores.emotion_score,
        "impact_score": report.scores.impact_score,
        "temporal_variance": report.scores.temporal_variance,
        "dark_pattern_score": report.dark_patterns.score,
        "dark_pattern_count": len(report.dark_patterns.patterns),
        "timeline_peaks": len(report.timeline.peaks),
        "overlay_elements": len(report.overlay),
        "report_path": str(Path(settings.DATA_DIR) / "reports" / job_id / "report.json"),
    }


def _friendly_error(stage: str, exc: Exception) -> str:
    """Map common exceptions to user-facing messages."""
    msg = str(exc)

    if stage == "analyzing":
        if "CUDA out of memory" in msg or "OutOfMemoryError" in msg:
            return (
                "Not enough GPU memory for analysis. "
                "TRIBE v2 needs ~16GB VRAM. Check your GPU with `make check-gpu`."
            )
        if "tribev2" in msg.lower() or "TribeModel" in msg:
            return (
                "Brain analysis failed. Ensure TRIBE v2 is installed: "
                "clone https://github.com/facebookresearch/tribev2 and run `pip install -e .`"
            )
        if "HF_TOKEN" in msg or "HuggingFace" in msg:
            return (
                "HuggingFace token missing or invalid. "
                "Add HF_TOKEN to your .env file. "
                "Get one at https://huggingface.co/settings/tokens"
            )
        if "not loaded" in msg.lower():
            return (
                "TRIBE v2 model not loaded. Run `make setup` to download the model, "
                "or check GPU availability with `make check-gpu`."
            )
        if "not found" in msg.lower() or "FileNotFoundError" in type(exc).__name__:
            return f"Capture artifacts missing — the capture may have failed: {msg}"

    if stage == "scoring":
        if "atlas" in msg.lower() or "nibabel" in msg.lower() or "nilearn" in msg.lower():
            return (
                "Brain region atlas could not be loaded. "
                "Ensure nibabel and nilearn are installed: pip install nibabel nilearn"
            )
        if "predictions" in msg.lower() or "shape" in msg.lower():
            return (
                "Analysis produced unexpected results. "
                "This may be a TRIBE v2 compatibility issue."
            )
        return f"Scoring engine failed: {msg}"

    return msg


async def _process_job(job_id: str) -> None:
    url_row = await _get_job_url(job_id)
    if url_row is None:
        return
    url = url_row
    try:
        # Stage 1: URL validation
        await _update_job(job_id, JobStatus.validating, None, None)
        validated = await asyncio.to_thread(validate_url, url)

        # Stage 2: Website capture (Playwright)
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
            JobStatus.capturing,
            None,
            None,
            capture_metadata=artifacts,
        )

        # Stage 3: TRIBE v2 brain analysis (GPU inference)
        await _update_job(job_id, JobStatus.analyzing, None, None)
        logger.info("Starting TRIBE v2 inference for job %s", job_id)
        inference_meta = await asyncio.to_thread(_run_inference_sync, job_id)
        logger.info(
            "TRIBE v2 inference complete for job %s — %d timesteps",
            job_id,
            inference_meta.get("n_timesteps", 0),
        )

        # Stage 4: Core engine scoring (deterministic)
        await _update_job(job_id, JobStatus.scoring, None, None)
        logger.info("Starting core engine scoring for job %s", job_id)
        scoring_meta = await asyncio.to_thread(
            _run_scoring_sync, job_id, url, inference_meta
        )
        logger.info(
            "Scoring complete for job %s — impact=%.1f, dark_patterns=%d",
            job_id,
            scoring_meta.get("impact_score", 0),
            scoring_meta.get("dark_pattern_count", 0),
        )

        # Stage 5: Done
        await _update_job(
            job_id,
            JobStatus.ready,
            None,
            None,
            capture_metadata={
                **(artifacts or {}),
                "inference": inference_meta,
                "scoring": scoring_meta,
            },
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

        friendly = _friendly_error(stage.value, e)
        logger.error("Job %s failed at %s: %s", job_id, stage.value, e, exc_info=True)
        await _update_job(
            job_id,
            JobStatus.failed,
            failed_stage=stage.value,
            error_message=friendly,
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
