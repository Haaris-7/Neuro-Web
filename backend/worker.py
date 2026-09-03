import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from config import settings
from database import get_db
from models.job import JobStatus
from pipeline.capture import capture_website
from pipeline.url_validator import validate_url

logger = logging.getLogger(__name__)

IDLE_POLL_S = 0.5


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _update_job(
    job_id: str,
    status: JobStatus,
    *,
    failed_stage: str | None = None,
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    async with get_db() as db:
        if metadata is not None:
            await db.execute(
                """
                UPDATE jobs SET status = ?, failed_stage = ?, error_message = ?,
                                capture_metadata = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.value, failed_stage, error_message, json.dumps(metadata), _utc_now(), job_id),
            )
        else:
            await db.execute(
                "UPDATE jobs SET status = ?, failed_stage = ?, error_message = ?, updated_at = ? WHERE id = ?",
                (status.value, failed_stage, error_message, _utc_now(), job_id),
            )


async def _fetch_next_queued() -> tuple[str, str] | None:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT id, url FROM jobs WHERE status = ? ORDER BY created_at ASC LIMIT 1",
            (JobStatus.queued.value,),
        )
        row = await cur.fetchone()
    return (str(row["id"]), str(row["url"])) if row else None


async def _current_status(job_id: str) -> JobStatus:
    async with get_db() as db:
        cur = await db.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        row = await cur.fetchone()
    try:
        return JobStatus(str(row["status"])) if row else JobStatus.validating
    except ValueError:
        return JobStatus.validating


def _run_inference(job_id: str) -> dict[str, Any]:
    from pipeline.inference import run_inference

    return run_inference(job_id)


def _run_scoring(job_id: str, url: str, inference_meta: dict[str, Any], capture_meta: dict[str, Any]) -> dict[str, Any]:
    from engine.report import compile_report

    predictions = np.load(inference_meta["predictions_path"])["preds"]
    report = compile_report(
        job_id=job_id,
        url=url,
        predictions=predictions,
        segment_alignment=inference_meta["segment_alignment"],
        capture_dir=Path(settings.DATA_DIR).resolve() / "captures" / job_id,
        inference_meta=inference_meta,
        capture_meta=capture_meta,
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
    }


def _friendly_error(stage: JobStatus, exc: Exception) -> str:
    msg = str(exc)
    lowered = msg.lower()
    if stage == JobStatus.capturing:
        if "ffmpeg" in lowered:
            return msg
        if "screenshot" in lowered and "timeout" in lowered:
            return "Taking the page screenshot timed out. The page may be extremely long or heavy."
        if "timeout" in lowered:
            return "The page took too long to load. Try again or choose a lighter page."
        if "executable doesn't exist" in lowered or "playwright install" in lowered:
            return "Chromium is not installed for Playwright. Run `playwright install chromium`."
        return f"Website capture failed: {msg}"
    if stage == JobStatus.analyzing:
        if "out of memory" in lowered:
            return (
                "The GPU ran out of memory. Set TRIBE_MODALITIES=video to skip the text encoder, "
                "or use a GPU with more VRAM."
            )
        if "not loaded" in lowered or "tribev2" in lowered or "cuda" in lowered:
            return f"TRIBE v2 is unavailable: {msg}"
        if "gated" in lowered or "401" in msg or "hf_token" in lowered:
            return "HuggingFace rejected the download. Check HF_TOKEN and Llama-3.2-3B access."
        return f"Brain analysis failed: {msg}"
    if stage == JobStatus.scoring:
        return f"Scoring failed: {msg}"
    return msg


async def _process_job(job_id: str, url: str) -> None:
    try:
        await _update_job(job_id, JobStatus.validating)
        validated = await asyncio.to_thread(validate_url, url)

        await _update_job(job_id, JobStatus.capturing)
        capture_meta = await capture_website(
            job_id,
            validated,
            {
                "data_dir": settings.DATA_DIR,
                "viewport_w": settings.CAPTURE_VIEWPORT_W,
                "viewport_h": settings.CAPTURE_VIEWPORT_H,
                "capture_duration": settings.CAPTURE_DURATION,
                "navigation_timeout_ms": max(settings.CAPTURE_DURATION * 1000, 60000),
                "default_timeout_ms": 30000,
                "max_redirects": settings.MAX_REDIRECTS,
                "max_video_size_mb": settings.MAX_VIDEO_SIZE_MB,
                "require_transcode": settings.INFERENCE_BACKEND == "tribe",
            },
        )
        await _update_job(job_id, JobStatus.analyzing, metadata=capture_meta)

        logger.info("Job %s: inference (%s)", job_id, settings.INFERENCE_BACKEND)
        inference_meta = await asyncio.to_thread(_run_inference, job_id)

        await _update_job(job_id, JobStatus.scoring)
        scoring_meta = await asyncio.to_thread(
            _run_scoring, job_id, validated, inference_meta, capture_meta
        )
        logger.info(
            "Job %s ready: impact=%.1f dark_patterns=%d",
            job_id,
            scoring_meta["impact_score"],
            scoring_meta["dark_pattern_count"],
        )
        await _update_job(
            job_id,
            JobStatus.ready,
            metadata={
                **capture_meta,
                "inference": {k: v for k, v in inference_meta.items() if k != "segment_alignment"},
                "scoring": scoring_meta,
            },
        )
    except Exception as exc:
        stage = await _current_status(job_id)
        logger.error("Job %s failed at %s: %s", job_id, stage.value, exc, exc_info=True)
        await _update_job(
            job_id,
            JobStatus.failed,
            failed_stage=stage.value,
            error_message=_friendly_error(stage, exc),
        )


async def worker_loop(stop: asyncio.Event, model_ready: asyncio.Future | None = None) -> None:
    """Process queued jobs one at a time; waits for model loading before the first job."""
    while not stop.is_set():
        job = await _fetch_next_queued()
        if job is None:
            try:
                await asyncio.wait_for(stop.wait(), timeout=IDLE_POLL_S)
            except asyncio.TimeoutError:
                pass
            continue
        if model_ready is not None and not model_ready.done():
            logger.info("Job %s queued until the model finishes loading", job[0])
            await asyncio.wait({model_ready})
        await _process_job(*job)
