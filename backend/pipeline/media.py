import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _ffmpeg_binary(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if name == "ffmpeg":
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return None
    return None


def ffmpeg_available() -> bool:
    return _ffmpeg_binary("ffmpeg") is not None


def transcode_to_mp4(
    source: Path,
    target: Path,
    *,
    start_s: float = 0.0,
    duration_s: float | None = None,
    timeout_s: int = 300,
) -> Path | None:
    """Re-encode a Playwright WebM to H.264 MP4, optionally trimmed to a window.

    Playwright's WebM output has no duration in the container header, which
    breaks moviepy/ffprobe-based readers. Returns None when ffmpeg is missing
    or the transcode fails so callers can fall back to the original file.
    """
    ffmpeg = _ffmpeg_binary("ffmpeg")
    if ffmpeg is None:
        logger.warning("ffmpeg not found; keeping WebM capture without transcode")
        return None
    trim: list[str] = []
    if start_s > 0:
        trim += ["-ss", f"{start_s:.3f}"]
    if duration_s is not None and duration_s > 0:
        trim += ["-t", f"{duration_s:.3f}"]
    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        *trim,
        "-i",
        str(source),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-movflags",
        "+faststart",
        str(target),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("ffmpeg transcode failed: %s", exc)
        return None
    if result.returncode != 0 or not target.exists():
        logger.warning("ffmpeg transcode failed: %s", result.stderr.strip()[-500:])
        target.unlink(missing_ok=True)
        return None
    return target


def probe_duration(path: Path) -> float | None:
    ffprobe = _ffmpeg_binary("ffprobe")
    if ffprobe is None:
        return None
    cmd = [
        ffprobe,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    candidates = [info.get("format", {}).get("duration")]
    candidates += [s.get("duration") for s in info.get("streams", [])]
    for value in candidates:
        try:
            duration = float(value)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return duration
    return None
