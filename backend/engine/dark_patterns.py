"""Rule-based detection of six dark-pattern categories (Brignull taxonomy).

Text heuristics run over the page's visible text; evidence is then anchored to
page coordinates via the DOM snapshot so it can be drawn on the overlay.
Layout heuristics (misdirection) and control state (pre-checked boxes) use the
snapshot directly.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

PATTERN_TYPES = (
    "urgency",
    "confirmshaming",
    "pre_checked",
    "hidden_costs",
    "misdirection",
    "forced_continuity",
)

TYPE_WEIGHTS: dict[str, float] = {
    "urgency": 1.5,
    "confirmshaming": 2.0,
    "pre_checked": 1.5,
    "hidden_costs": 2.0,
    "misdirection": 1.5,
    "forced_continuity": 1.5,
}

MAX_EVIDENCE_CHARS = 220
MAX_MATCHES_PER_TYPE = 8
MAX_BUTTON_LABEL_CHARS = 48
MAX_BUTTON_ROW_GAP_PX = 700
MIN_PX_PER_CHAR = 5.0


@dataclass(frozen=True)
class DarkPatternMatch:
    pattern_type: str
    confidence: float
    evidence_text: str
    bbox: dict[str, float] | None = None


@dataclass
class DarkPatternReport:
    patterns: list[DarkPatternMatch] = field(default_factory=list)
    score: float = 0.0
    summary: str = ""
    counts: dict[str, int] = field(default_factory=dict)


_URGENCY_STRONG = re.compile(
    r"(?i)\b(?:"
    r"only\s+\d+\s+(?:left|remaining|in\s+stock|spots?|seats?|rooms?)|"
    r"expires?\s+(?:in|soon|today|tomorrow|at\s+midnight)|"
    r"limited[\s-]+(?:time|offer|quantity|stock|supply)|"
    r"hurry|act\s+now|order\s+now|don'?t\s+miss\s+out|last\s+chance|"
    r"while\s+(?:supplies|stocks?)\s+last|selling\s+fast|"
    r"(?:sale|offer|deal)\s+ends?\s+(?:tonight|today|soon|in)|"
    r"time\s+is\s+running\s+out|"
    r"\d+\s+(?:people|others)\s+(?:are\s+)?(?:viewing|looking\s+at)\s+this"
    r")\b"
)
_URGENCY_MODERATE = re.compile(
    r"(?i)\b(?:"
    r"limited\s+availability|almost\s+gone|few\s+left|going\s+fast|"
    r"offer\s+ends|today\s+only|flash\s+sale|countdown|"
    r"in\s+high\s+demand|booked\s+\d+\s+times"
    r")\b"
)
_URGENCY_TIMER = re.compile(
    r"(?i)(?:\b\d{1,2}\s*:\s*\d{2}\s*:\s*\d{2}\b|"
    r"\b\d+\s*(?:hours?|hrs?|minutes?|mins?|seconds?|secs?)\s+(?:left|remaining)\b)"
)

_CONFIRM_STRONG = re.compile(
    r"(?i)(?:"
    r"no\s+thanks?,?\s+i\s+(?:hate|don'?t\s+want|prefer\s+not|like\s+paying\s+more|enjoy\s+overpaying|love\s+full\s+price)[^.\n]{0,60}|"
    r"no,?\s+i\s+don'?t\s+want\s+(?:to\s+)?(?:save|the\s+savings|this\s+deal|a\s+discount|discounts?|offers?)[^.\n]{0,40}|"
    r"i\s+(?:prefer|want|choose)\s+to\s+(?:pay\s+(?:more|full\s+price)|miss\s+out|lose\s+money|stay\s+uninformed)[^.\n]{0,40}|"
    r"i(?:'|’)?ll\s+pass\s+on\s+(?:this\s+deal|saving|the\s+discount)[^.\n]{0,40}"
    r")"
)
_CONFIRM_MODERATE = re.compile(
    r"(?i)(?:"
    r"no\s+thanks?,?\s+i\s+(?:don'?t\s+need|am\s+not\s+interested)[^.\n]{0,60}|"
    r"maybe\s+later,?\s+i\s+(?:don'?t\s+mind\s+missing|am\s+ok\s+missing)[^.\n]{0,40}|"
    r"i\s+(?:don'?t|do\s+not)\s+(?:want|care\s+about)\s+(?:to\s+)?(?:save|saving|savings|deals|discounts)[^.\n]{0,40}"
    r")"
)

_PRECHECK_TEXT = re.compile(
    r"(?i)(?:"
    r"pre[- ]?(?:checked|selected|ticked)|"
    r"(?:checked|selected|ticked)\s+by\s+default|"
    r"you\s+will\s+be\s+subscribed\s+unless|"
    r"uncheck\s+(?:this\s+|the\s+)?box\s+(?:if\s+you|to\s+opt\s+out)"
    r")"
)
_PRECHECK_LABEL = re.compile(
    r"(?i)(?:subscribe|newsletter|marketing|promotional|offers?|partners?|third[- ]part|"
    r"share\s+my|insurance|protection\s+plan|donat|tip|add\s+.{0,20}for\s+(?:\$|€|£)|"
    r"agree\s+to\s+receive|keep\s+me\s+(?:updated|informed|posted))"
)

_HIDDEN_FEE_PHRASES = re.compile(
    r"(?i)\b(?:"
    r"additional\s+(?:fees?|charges?|costs?)|service\s+(?:fee|charge)|processing\s+fee|"
    r"convenience\s+fee|handling\s+fee|resort\s+fee|booking\s+fee|"
    r"shipping\s+(?:not\s+included|extra|calculated\s+at\s+checkout)|"
    r"taxes?\s+(?:and\s+fees\s+)?(?:not\s+included|extra|additional|may\s+apply)|"
    r"(?:extra|additional|other)\s+charges?\s+may\s+apply|fees?\s+(?:may\s+)?apply|"
    r"plus\s+(?:applicable\s+)?(?:tax|taxes|shipping|handling|fees)|"
    r"(?:does\s+not|doesn'?t)\s+include\s+(?:shipping|tax|taxes|fees?)|"
    r"excl(?:\.|uding|usive\s+of)\s+(?:vat|tax|taxes|shipping)"
    r")\b"
)

_FORCED_STRONG = re.compile(
    r"(?i)(?:"
    r"free\s+trial[^.\n]{0,80}?(?:then|after\s+which|billed|charged|\$|€|£)|"
    r"(?:credit|debit)\s+card\s+required|card\s+required\s+for\s+(?:the\s+)?trial|"
    r"auto(?:matic(?:ally)?)?[- ]?renew(?:s|al|ed)?|automatically\s+(?:charged|billed)|"
    r"billed\s+(?:automatically|annually|monthly)\s+(?:until|unless)\s+(?:you\s+)?cancel|"
    r"you\s+will\s+be\s+charged\s+(?:after|when|once)\s+(?:the|your)\s+trial"
    r")"
)
_FORCED_MODERATE = re.compile(
    r"(?i)(?:"
    r"cancel\s+anytime|renews?\s+automatically|subscription\s+(?:renews|continues)|"
    r"recurring\s+(?:billing|payment|charge)|first\s+\d+\s+(?:days?|months?|weeks?)\s+free"
    r")"
)


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def _snippet(text: str) -> str:
    text = " ".join(text.split())
    if len(text) > MAX_EVIDENCE_CHARS:
        return text[: MAX_EVIDENCE_CHARS - 3] + "..."
    return text


def _text_matches(
    pattern_type: str, regex: re.Pattern[str], text: str, confidence: float
) -> list[DarkPatternMatch]:
    matches = []
    for m in regex.finditer(text):
        snippet = _snippet(m.group(0))
        if len(snippet) < 3:
            continue
        matches.append(DarkPatternMatch(pattern_type, _clip(confidence), snippet))
    return matches


def _detect_urgency(text: str) -> list[DarkPatternMatch]:
    return (
        _text_matches("urgency", _URGENCY_STRONG, text, 0.9)
        + _text_matches("urgency", _URGENCY_MODERATE, text, 0.6)
        + _text_matches("urgency", _URGENCY_TIMER, text, 0.5)
    )


def _detect_confirmshaming(text: str, controls: list[dict[str, Any]]) -> list[DarkPatternMatch]:
    matches = _text_matches("confirmshaming", _CONFIRM_STRONG, text, 0.9)
    matches += _text_matches("confirmshaming", _CONFIRM_MODERATE, text, 0.6)
    for control in controls:
        label = str(control.get("text") or control.get("aria_label") or "")
        if not label:
            continue
        if _CONFIRM_STRONG.search(label) or _CONFIRM_MODERATE.search(label):
            matches.append(
                DarkPatternMatch("confirmshaming", 0.95, _snippet(label), _bbox(control))
            )
    return matches


def _detect_pre_checked(text: str, checked_boxes: list[dict[str, Any]]) -> list[DarkPatternMatch]:
    matches = []
    for box in checked_boxes:
        label = str(box.get("label", ""))
        if _PRECHECK_LABEL.search(label):
            matches.append(
                DarkPatternMatch("pre_checked", 0.9, _snippet(label or "pre-checked option"), _bbox(box))
            )
    matches += _text_matches("pre_checked", _PRECHECK_TEXT, text, 0.5)
    return matches


def _detect_hidden_costs(text: str) -> list[DarkPatternMatch]:
    return _text_matches("hidden_costs", _HIDDEN_FEE_PHRASES, text, 0.8)


def _detect_forced_continuity(text: str) -> list[DarkPatternMatch]:
    return _text_matches("forced_continuity", _FORCED_STRONG, text, 0.85) + _text_matches(
        "forced_continuity", _FORCED_MODERATE, text, 0.5
    )


def _bbox(item: dict[str, Any]) -> dict[str, float]:
    return {
        "x": float(item.get("x", 0.0)),
        "y": float(item.get("y", 0.0)),
        "width": float(item.get("width", 0.0)),
        "height": float(item.get("height", 0.0)),
    }


def _area(item: dict[str, Any]) -> float:
    return max(0.0, float(item.get("width", 0.0)) * float(item.get("height", 0.0)))


def _has_visible_label(control: dict[str, Any]) -> bool:
    """Screen-reader-only text survives innerText; a label needs room to render."""
    text = str(control.get("text") or "")
    if not text or len(text) > MAX_BUTTON_LABEL_CHARS:
        return False
    needed_px = min(len(text) * MIN_PX_PER_CHAR, 60.0)
    return float(control.get("width", 0.0)) >= needed_px


def _detect_misdirection(controls: list[dict[str, Any]]) -> list[DarkPatternMatch]:
    """Flag rows where one button dwarfs a visibly labelled sibling (accept vs. decline)."""
    sized = [c for c in controls if c.get("is_button") and _area(c) > 1.0 and _has_visible_label(c)]
    if len(sized) < 2:
        return []
    sized.sort(key=lambda c: (float(c.get("y", 0.0)), float(c.get("x", 0.0))))
    rows: list[list[dict[str, Any]]] = []
    for control in sized:
        y = float(control.get("y", 0.0))
        for row in rows:
            if abs(y - float(row[0].get("y", 0.0))) <= 24.0:
                row.append(control)
                break
        else:
            rows.append([control])

    matches = []
    for row in rows:
        if len(row) < 2:
            continue
        largest = max(row, key=_area)
        smallest = min(row, key=_area)
        ratio = _area(largest) / _area(smallest)
        if ratio < 3.5:
            continue
        gap = abs(float(largest.get("x", 0.0)) - float(smallest.get("x", 0.0)))
        if gap > MAX_BUTTON_ROW_GAP_PX:
            continue
        confidence = _clip(0.4 + min(0.4, (ratio - 3.5) * 0.05))
        big_label = _snippet(str(largest.get("text", ""))) or "<unlabelled>"
        small_label = _snippet(str(smallest.get("text", ""))) or "<unlabelled>"
        evidence = (
            f'"{big_label}" is {ratio:.1f}x larger than "{small_label}" in the same row'
        )
        matches.append(DarkPatternMatch("misdirection", confidence, evidence, _bbox(largest)))
    return matches


def _anchor(match: DarkPatternMatch, blocks: list[dict[str, Any]]) -> DarkPatternMatch:
    if match.bbox is not None:
        return match
    needle = match.evidence_text.rstrip(".").lower()
    if needle.endswith("..."):
        needle = needle[:-3]
    if len(needle) < 3:
        return match
    for block in blocks:
        if needle in " ".join(str(block.get("text", "")).split()).lower():
            return DarkPatternMatch(match.pattern_type, match.confidence, match.evidence_text, _bbox(block))
    return match


def _dedupe(matches: list[DarkPatternMatch]) -> list[DarkPatternMatch]:
    by_type: dict[str, list[DarkPatternMatch]] = defaultdict(list)
    for m in matches:
        by_type[m.pattern_type].append(m)
    kept: list[DarkPatternMatch] = []
    for group in by_type.values():
        group.sort(key=lambda m: (-m.confidence, -len(m.evidence_text)))
        seen: list[str] = []
        for m in group:
            key = m.evidence_text.lower()
            if any(key == s or key in s for s in seen):
                continue
            seen.append(key)
            kept.append(m)
            if len(seen) >= MAX_MATCHES_PER_TYPE:
                break
    kept.sort(key=lambda m: (PATTERN_TYPES.index(m.pattern_type), -m.confidence))
    return kept


def _score(matches: list[DarkPatternMatch]) -> float:
    return min(10.0, sum(m.confidence * TYPE_WEIGHTS[m.pattern_type] for m in matches))


def _summary(matches: list[DarkPatternMatch], counts: dict[str, int], score: float) -> str:
    if not matches:
        return "No dark-pattern signals were found in the page text or layout."
    parts = [f"{k.replace('_', ' ')} ({v})" for k, v in counts.items()]
    return (
        f"Detected {len(matches)} manipulative-design signal(s): {', '.join(parts)}. "
        f"Weighted concern score {score:.1f}/10."
    )


def detect_dark_patterns(text: str, dom: dict[str, Any] | None = None) -> DarkPatternReport:
    dom = dom or {}
    controls = [r for r in dom.get("regions", []) if r.get("is_control")]
    blocks = list(dom.get("text_blocks", [])) + controls
    checked = list(dom.get("checked_boxes", []))

    collected: list[DarkPatternMatch] = []
    collected += _detect_urgency(text)
    collected += _detect_confirmshaming(text, controls)
    collected += _detect_pre_checked(text, checked)
    collected += _detect_hidden_costs(text)
    collected += _detect_forced_continuity(text)
    collected += _detect_misdirection(controls)

    matches = _dedupe([_anchor(m, blocks) for m in collected])
    counts: dict[str, int] = {}
    for m in matches:
        counts[m.pattern_type] = counts.get(m.pattern_type, 0) + 1
    score = _score(matches)
    return DarkPatternReport(
        patterns=matches, score=score, summary=_summary(matches, counts, score), counts=counts
    )
