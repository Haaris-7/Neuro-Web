"""Build TRIBE v2 event DataFrames directly from capture artifacts.

TRIBE v2's stock ``get_events_dataframe`` derives word timings by running
text-to-speech and then transcribing the audio with whisperx. A silent screen
recording has no audio and page text has no inherent timing, so instead this
module simulates a reader following the scroll and emits Word events aligned
with the Video event on one shared timeline. Audio extractors are never loaded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

TIMELINE = "default"
SUBJECT = "default"
LANGUAGE = "english"
VIDEO_CHUNK_MAX_S = 60.0
VIDEO_CHUNK_MIN_S = 30.0

_WORD_RE = re.compile(r"\S+")
_HAS_ALNUM_RE = re.compile(r"[^\W_]", re.UNICODE)
_TERMINAL_PUNCT = ".!?:;"


@dataclass(frozen=True)
class TextBlock:
    text: str
    y: float
    height: float


def _visible_window(
    block: TextBlock, scroll_timeline: list[dict[str, float]], viewport_h: float
) -> tuple[float, float] | None:
    """Return the [enter, exit) interval (seconds) during which the block is on screen."""
    enter: float | None = None
    exit_t: float | None = None
    for sample in scroll_timeline:
        t = float(sample["time_ms"]) / 1000.0
        top = float(sample["scroll_y"])
        on_screen = block.y < top + viewport_h and block.y + block.height > top
        if on_screen and enter is None:
            enter = t
        elif not on_screen and enter is not None and exit_t is None:
            exit_t = t
            break
    if enter is None:
        return None
    if exit_t is None:
        exit_t = float("inf")
    return enter, exit_t


def _tokenize(text: str) -> list[str]:
    words = []
    for match in _WORD_RE.finditer(text):
        token = match.group(0).strip("\u200b\ufeff")
        if len(token) > 40 or not _HAS_ALNUM_RE.search(token):
            continue
        words.append(token)
    return words


def schedule_words(
    blocks: list[TextBlock],
    scroll_timeline: list[dict[str, float]],
    viewport_h: float,
    duration_s: float,
    *,
    words_per_minute: float,
    context_words: int,
) -> list[dict[str, Any]]:
    """Simulate a reader skimming the page as it scrolls.

    Blocks are read in the order they enter the viewport. Reading proceeds at a
    fixed pace; a block still unread when it leaves the viewport is skipped, and
    reading stops when the recording ends. Each word carries a rolling context
    of preceding words, ending with the word itself, as the text encoder expects.
    """
    if words_per_minute <= 0:
        raise ValueError("words_per_minute must be positive")
    word_dt = 60.0 / words_per_minute
    windows: list[tuple[float, float, TextBlock]] = []
    for block in blocks:
        window = _visible_window(block, scroll_timeline, viewport_h)
        if window is not None:
            windows.append((window[0], window[1], block))
    windows.sort(key=lambda w: (w[0], w[2].y))

    history: list[str] = []
    rows: list[dict[str, Any]] = []
    cursor = 0.0
    for enter, exit_t, block in windows:
        start = max(cursor, enter)
        if start >= exit_t or start >= duration_s:
            continue
        for word in _tokenize(block.text):
            if start + word_dt > min(exit_t, duration_s):
                break
            context = " ".join(history[-context_words:] + [word])
            rows.append(
                {
                    "type": "Word",
                    "text": word,
                    "context": context,
                    "start": round(start, 3),
                    "duration": round(word_dt, 3),
                    "timeline": TIMELINE,
                    "subject": SUBJECT,
                    "language": LANGUAGE,
                }
            )
            history.append(word)
            start += word_dt
        cursor = start
        if history and history[-1][-1] not in _TERMINAL_PUNCT:
            history[-1] += "."
    return rows


def text_blocks_from_dom(dom: dict[str, Any]) -> list[TextBlock]:
    blocks = []
    for item in dom.get("text_blocks", []):
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        blocks.append(
            TextBlock(
                text=text,
                y=float(item.get("y", 0.0)),
                height=float(item.get("height", 0.0)),
            )
        )
    return blocks


def video_event(video_path: Path) -> dict[str, Any]:
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    return {
        "type": "Video",
        "filepath": str(video_path.resolve()),
        "start": 0.0,
        "timeline": TIMELINE,
        "subject": SUBJECT,
    }


def build_events(
    *,
    video_path: Path | None,
    word_rows: list[dict[str, Any]] | None,
) -> pd.DataFrame:
    """Assemble and standardise a TRIBE-ready events DataFrame.

    Requires the ``neuralset`` package that ships with ``tribev2``. Video events
    are chunked exactly as TRIBE v2 does internally to bound extractor memory.
    """
    from neuralset.events.transforms import ChunkEvents
    from neuralset.events.utils import standardize_events

    rows: list[dict[str, Any]] = []
    if video_path is not None:
        rows.append(video_event(video_path))
    if word_rows:
        rows.extend(word_rows)
    if not rows:
        raise ValueError("No events to build: enable at least one modality with content")

    events = standardize_events(pd.DataFrame(rows))
    if video_path is not None:
        chunker = ChunkEvents(
            event_type_to_chunk="Video",
            max_duration=VIDEO_CHUNK_MAX_S,
            min_duration=VIDEO_CHUNK_MIN_S,
        )
        events = chunker(events)
        events = standardize_events(events)
    return events
