"""Custom TRIBE v2 events pipeline that constructs video-only events, bypassing audio extraction.

TRIBE v2's ``get_events_dataframe(video_path=...)`` internally runs ``ExtractAudioFromVideo``
which loads Wav2Vec-BERT and runs the full audio pipeline. This wrapper builds a minimal
events DataFrame containing only the Video event row so the model processes the video
through V-JEPA2 without touching the audio extractor — significantly reducing VRAM usage.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_VIDEO_EVENT_COLUMNS = [
    "type",
    "filepath",
    "start",
    "duration",
    "timeline",
    "subject",
]


def get_video_only_events(
    video_path: str,
    *,
    subject: str = "default",
    timeline: str = "default",
) -> pd.DataFrame:
    """Build a TRIBE v2-compatible events DataFrame with only a Video event.

    The returned DataFrame is accepted by ``TribeModel.predict(events=df)`` and
    causes the model to process only the video modality (V-JEPA2 encoder) while
    completely skipping audio feature extraction.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    duration = _probe_video_duration(str(path))

    row = {
        "type": "Video",
        "filepath": str(path.resolve()),
        "start": 0.0,
        "duration": duration,
        "timeline": timeline,
        "subject": subject,
    }
    df = pd.DataFrame([row], columns=_VIDEO_EVENT_COLUMNS)
    logger.info(
        "Built video-only events DataFrame — file=%s, duration=%.1fs",
        path.name,
        duration,
    )
    return df


def _probe_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe (preferred) or OpenCV fallback."""
    try:
        return _ffprobe_duration(video_path)
    except Exception:
        pass

    try:
        return _opencv_duration(video_path)
    except Exception:
        pass

    logger.warning("Could not probe video duration — using fallback of 30s")
    return 30.0


def _ffprobe_duration(video_path: str) -> float:
    import json
    import subprocess

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def _opencv_duration(video_path: str) -> float:
    import cv2

    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if fps > 0 and frames > 0:
            return frames / fps
    finally:
        cap.release()
    raise RuntimeError("OpenCV could not determine video duration")
