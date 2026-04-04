from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

TYPE_WEIGHTS: dict[str, float] = {
    "urgency": 1.5,
    "confirmshaming": 2.0,
    "pre_checked": 1.0,
    "hidden_costs": 2.0,
    "misdirection": 1.5,
    "forced_continuity": 1.5,
}


@dataclass(frozen=True)
class DarkPatternMatch:
    pattern_type: str
    confidence: float
    evidence_text: str
    dom_selector: str | None = None
    bbox: dict | None = None


@dataclass
class DarkPatternReport:
    patterns: list[DarkPatternMatch] = field(default_factory=list)
    score: float = 0.0
    summary: str = ""


_URGENCY_STRONG = re.compile(
    r"(?i)\b(?:"
    r"only\s+\d+\s+(?:left|remaining|in\s+stock|spots?|seats?)|"
    r"expires?\s+(?:in|soon|today|tomorrow|midnight)|"
    r"limited\s+(?:time|offer|quantity|stock|supply)|"
    r"\b(?:hurry|act\s+now|buy\s+now|order\s+now|don'?t\s+miss|last\s+chance)\b|"
    r"while\s+supplies\s+last|"
    r"selling\s+fast|"
    r"ends?\s+(?:tonight|today|soon|at\s+midnight)|"
    r"(?:clock|countdown)\s+is\s+ticking|"
    r"time\s+is\s+running\s+out"
    r")\b"
)

_URGENCY_MODERATE = re.compile(
    r"(?i)\b(?:"
    r"limited\s+availability|"
    r"almost\s+gone|"
    r"few\s+left|"
    r"going\s+fast|"
    r"offer\s+ends|"
    r"deadline|"
    r"today\s+only|"
    r"flash\s+sale|"
    r"countdown|"
    r"\b(?:timer|ticking)\b"
    r")\b"
)

_URGENCY_TIME_LIKE = re.compile(
    r"(?i)(?:\b\d{1,2}\s*:\s*\d{2}\s*:\s*\d{2}\b|"
    r"\b\d+\s*(?:hours?|hrs?|minutes?|mins?|seconds?|secs?)\s+(?:left|remaining)\b)"
)

_CONFIRM_STRONG = re.compile(
    r"(?i)(?:"
    r"no\s+thanks?,?\s+i\s+(?:hate|don'?t\s+want|prefer\s+not|like\s+paying\s+more)|"
    r"no,?\s+i\s+don'?t\s+want\s+(?:to\s+)?(?:save|the\s+savings|this\s+deal|discount|offers?)|"
    r"i(?:'|’)?ll\s+pass\s+on\s+this\s+deal|"
    r"no\s+thanks?,?\s+i\s+(?:enjoy\s+overpaying|love\s+full\s+price)|"
    r"i\s+prefer\s+to\s+(?:pay\s+more|miss\s+out|lose\s+money)"
    r")"
)

_CONFIRM_MODERATE = re.compile(
    r"(?i)(?:"
    r"no\s+thanks?,?\s+i\s+(?:don'?t\s+need|am\s+not\s+interested)|"
    r"maybe\s+later,?\s+i\s+(?:don'?t\s+mind\s+missing|am\s+ok\s+missing)|"
    r"i\s+choose\s+to\s+(?:decline|refuse|skip)\s+(?:this\s+)?(?:offer|deal|savings?)|"
    r"no,?\s+i\s+(?:want\s+to\s+pay\s+full\s+price|refuse\s+the\s+discount)|"
    r"i(?:'|’)?ll\s+pass(?:\s+on\s+(?:this|savings?|the\s+deal))?"
    r")"
)

_SIGNUP_NEAR = (
    r"(?:\bsubscribe\b|\bnewsletter\b|promotional\s+emails?|marketing\s+emails?|"
    r"terms\s*(?:and|&)\s*conditions?|\bi\s+agree\b|\bpayment\b|\bcheckout\b|"
    r"order\s+summary|\bsign\s*up\b)"
)

_PRECHECK_NEAR_SIGNUP = re.compile(
    r"(?is)(?:"
    r"(?:pre[- ]?checked|pre[- ]?selected|\[\s*checkbox|(?<![a-z])checkbox\b|check\s*box\b|"
    r"unless\s+you\s+uncheck|already\s+(?:checked|selected|opted\s*in|subscribed)|"
    r"uncheck\s+(?:the\s+)?box\s+to\s+opt\s*out|by\s+default\s+(?:checked|selected|subscribed))"
    r".{0,88}?"
    + _SIGNUP_NEAR
    + r"|"
    + _SIGNUP_NEAR
    + r".{0,88}?"
    r"(?:pre[- ]?checked|pre[- ]?selected|\[\s*checkbox|(?<![a-z])checkbox\b|check\s*box\b|"
    r"unless\s+you\s+uncheck|already\s+(?:checked|selected|opted\s*in|subscribed)|"
    r"uncheck\s+(?:the\s+)?box\s+to\s+opt\s*out)"
    r")"
)

_PRECHECK_SOFT = re.compile(
    r"(?i)(?:"
    r"pre[- ]?checked|pre[- ]?selected|"
    r"checkbox\s+is\s+(?:checked|selected|ticked)\s+by\s+default|"
    r"you\s+will\s+be\s+subscribed\s+unless|"
    r"subscribe(?:\s+to\s+our\s+newsletter)?\s*[,\.]?\s*(?:i\s+)?agree"
    r")"
)

_HIDDEN_FEE_PHRASES = re.compile(
    r"(?i)\b(?:"
    r"additional\s+(?:fee|fees|charge|charges|cost|costs)|"
    r"service\s+charge|processing\s+fee|convenience\s+fee|"
    r"shipping\s+(?:not\s+included|extra|additional|separate)|"
    r"taxes?\s+(?:not\s+included|extra|additional|may\s+apply)|"
    r"hidden\s+(?:fee|fees|cost|charge)|"
    r"extra\s+charges?\s+may\s+apply|"
    r"fees?\s+apply|"
    r"plus\s+(?:tax|shipping|handling)|"
    r"does\s+not\s+include\s+(?:shipping|tax|fees?)"
    r")\b"
)

_PRICE_LIKE = re.compile(
    r"(?:(?:USD|EUR|GBP|CA\$|US\$|\$|€|£)\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?|"
    r"\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|dollars?|euros?))\b",
    re.IGNORECASE,
)

_FORCED_STRONG = re.compile(
    r"(?i)(?:"
    r"free\s+trial(?:\s+ends|\s+then|\s+after)?|"
    r"credit\s+card\s+required|card\s+required\s+for\s+trial|"
    r"auto[- ]?renew(?:al)?|automatically\s+(?:renew|charged|billed)|"
    r"billed\s+automatically|"
    r"no\s+charge\s+until\s+(?:after|the\s+end)|"
    r"after\s+(?:your\s+)?(?:free\s+)?trial\s+(?:ends?|you\s+will\s+be\s+charged)"
    r")"
)

_FORCED_MODERATE = re.compile(
    r"(?i)(?:"
    r"cancel\s+anytime(?:\s+before)?|"
    r"renews?\s+automatically|"
    r"subscription\s+(?:renews|continues)|"
    r"recurring\s+billing|"
    r"you\s+will\s+be\s+charged\s+after|"
    r"trial\s+period\s+then\s+\$|"
    r"first\s+\d+\s+(?:days?|months?)\s+free"
    r")"
)


def _clip_confidence(x: float) -> float:
    return max(0.0, min(1.0, x))


def _add_text_matches(
    out: list[DarkPatternMatch],
    pattern_type: str,
    regex: re.Pattern[str],
    text: str,
    base_confidence: float,
    dom_selector: str | None = None,
) -> None:
    for m in regex.finditer(text):
        snippet = m.group(0).strip()
        if len(snippet) < 3:
            continue
        if len(snippet) > 220:
            snippet = snippet[:217] + "..."
        out.append(
            DarkPatternMatch(
                pattern_type=pattern_type,
                confidence=_clip_confidence(base_confidence),
                evidence_text=snippet,
                dom_selector=dom_selector,
                bbox=None,
            )
        )


def _detect_urgency(text: str) -> list[DarkPatternMatch]:
    matches: list[DarkPatternMatch] = []
    _add_text_matches(matches, "urgency", _URGENCY_STRONG, text, 0.92)
    _add_text_matches(matches, "urgency", _URGENCY_MODERATE, text, 0.55)
    _add_text_matches(matches, "urgency", _URGENCY_TIME_LIKE, text, 0.5)
    low_timer = re.compile(
        r"(?i)\b(?:countdown|timer)\s*(?:widget|block|banner)?\b"
    )
    _add_text_matches(matches, "urgency", low_timer, text, 0.35)
    return matches


def _detect_confirmshaming(text: str) -> list[DarkPatternMatch]:
    matches: list[DarkPatternMatch] = []
    _add_text_matches(matches, "confirmshaming", _CONFIRM_STRONG, text, 0.9)
    _add_text_matches(matches, "confirmshaming", _CONFIRM_MODERATE, text, 0.55)
    return matches


def _detect_pre_checked(text: str) -> list[DarkPatternMatch]:
    matches: list[DarkPatternMatch] = []
    for m in _PRECHECK_NEAR_SIGNUP.finditer(text):
        raw = m.group(0).strip()
        snippet = raw if len(raw) <= 220 else raw[:217] + "..."
        matches.append(
            DarkPatternMatch(
                pattern_type="pre_checked",
                confidence=0.62,
                evidence_text=snippet,
                dom_selector=None,
                bbox=None,
            )
        )
    _add_text_matches(matches, "pre_checked", _PRECHECK_SOFT, text, 0.45)
    return matches


def _detect_hidden_costs(text: str) -> list[DarkPatternMatch]:
    matches: list[DarkPatternMatch] = []
    _add_text_matches(matches, "hidden_costs", _HIDDEN_FEE_PHRASES, text, 0.85)
    prices = list(_PRICE_LIKE.finditer(text))
    if len(prices) >= 2:
        values: set[str] = set()
        for m in prices[:12]:
            norm = re.sub(r"[^\d.]", "", m.group(0))
            if norm:
                values.add(norm)
        if len(values) >= 2:
            span_start = prices[0].start()
            span_end = prices[-1].end()
            snippet = text[span_start:span_end].strip().replace("\n", " ")
            if len(snippet) > 200:
                snippet = snippet[:197] + "..."
            conf = 0.5 if len(values) == 2 else min(0.88, 0.5 + 0.12 * (len(values) - 2))
            matches.append(
                DarkPatternMatch(
                    pattern_type="hidden_costs",
                    confidence=_clip_confidence(conf),
                    evidence_text=snippet,
                    dom_selector=None,
                    bbox=None,
                )
            )
    return matches


def _detect_forced_continuity(text: str) -> list[DarkPatternMatch]:
    matches: list[DarkPatternMatch] = []
    _add_text_matches(matches, "forced_continuity", _FORCED_STRONG, text, 0.88)
    _add_text_matches(matches, "forced_continuity", _FORCED_MODERATE, text, 0.52)
    low = text.lower()
    ft = re.search(r"\bfree\s+trial\b", low)
    pay = re.search(
        r"\b(?:credit\s+card|payment\s+method|card\s+on\s+file)\b",
        low,
    )
    if ft and pay:
        i, j = sorted((ft.start(), pay.start()))
        if j - i <= 360:
            span = text[i : min(len(text), max(ft.end(), pay.end()) + 40)].strip()
            snippet = span if len(span) <= 220 else span[:217] + "..."
            matches.append(
                DarkPatternMatch(
                    pattern_type="forced_continuity",
                    confidence=0.72,
                    evidence_text=snippet,
                    dom_selector=None,
                    bbox=None,
                )
            )
    return matches


def _box_area(b: dict) -> float:
    w = float(b.get("width") or 0)
    h = float(b.get("height") or 0)
    return max(0.0, w * h)


def _interactive_tag(tag: str) -> bool:
    return tag.strip().lower() in {"button", "a"}


def _detect_misdirection(boxes: list[dict]) -> list[DarkPatternMatch]:
    if not boxes:
        return []
    inter = [b for b in boxes if _interactive_tag(str(b.get("tag", "")))]
    if len(inter) < 2:
        return []
    inter.sort(key=lambda b: (float(b.get("y", 0)), float(b.get("x", 0))))
    clusters: list[list[dict]] = []

    def _fits_row(cluster: list[dict], y: float) -> bool:
        return any(abs(y - float(c.get("y", 0))) <= 22.0 for c in cluster)

    for b in inter:
        y = float(b.get("y", 0))
        merged = False
        for cl in clusters:
            if _fits_row(cl, y):
                cl.append(b)
                merged = True
                break
        if not merged:
            clusters.append([b])
    matches: list[DarkPatternMatch] = []
    for group in clusters:
        if len(group) < 2:
            continue
        areas = [_box_area(b) for b in group]
        areas = [a for a in areas if a > 1.0]
        if len(areas) < 2:
            continue
        ratio = max(areas) / min(areas)
        if ratio < 3.25:
            continue
        largest = max(group, key=_box_area)
        smallest = min(group, key=_box_area)
        conf = _clip_confidence(0.42 + min(0.38, (ratio - 3.25) * 0.06))
        evidence = (
            f"Interactive control size ratio ~{ratio:.1f}x in the same row "
            f"(largest {int(_box_area(largest))}px² vs smallest {int(_box_area(smallest))}px²)"
        )
        matches.append(
            DarkPatternMatch(
                pattern_type="misdirection",
                confidence=conf,
                evidence_text=evidence,
                dom_selector=str(largest.get("tag")),
                bbox={
                    "tag": largest.get("tag"),
                    "x": largest.get("x"),
                    "y": largest.get("y"),
                    "width": largest.get("width"),
                    "height": largest.get("height"),
                    "scroll_y": largest.get("scroll_y"),
                },
            )
        )
    return matches


def _dedupe_matches(matches: list[DarkPatternMatch]) -> list[DarkPatternMatch]:
    seen: set[tuple[str, str, str | None]] = set()
    out: list[DarkPatternMatch] = []
    for m in matches:
        key = (m.pattern_type, m.evidence_text[:120], m.dom_selector)
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def _drop_subsumed_evidence(matches: list[DarkPatternMatch]) -> list[DarkPatternMatch]:
    by_type: dict[str, list[DarkPatternMatch]] = defaultdict(list)
    for m in matches:
        by_type[m.pattern_type].append(m)
    resolved: list[DarkPatternMatch] = []
    for ptype, group in by_type.items():
        if ptype == "misdirection":
            resolved.extend(group)
            continue
        ordered = sorted(group, key=lambda x: (-x.confidence, -len(x.evidence_text)))
        kept: list[DarkPatternMatch] = []
        for m in ordered:
            if any(
                m.evidence_text != k.evidence_text and m.evidence_text in k.evidence_text
                for k in kept
            ):
                continue
            kept.append(m)
        resolved.extend(kept)
    return resolved


def _compute_score(matches: list[DarkPatternMatch]) -> float:
    raw = sum(m.confidence * TYPE_WEIGHTS.get(m.pattern_type, 1.0) for m in matches)
    return min(10.0, raw)


def _build_summary(matches: list[DarkPatternMatch], score: float) -> str:
    if not matches:
        return "No dark pattern signals detected in the supplied text and layout data."
    counts: dict[str, int] = defaultdict(int)
    for m in matches:
        counts[m.pattern_type] += 1
    parts = [f"{k.replace('_', ' ')} ({v})" for k, v in sorted(counts.items())]
    types_str = ", ".join(parts)
    return (
        f"Detected {len(matches)} manipulative-design signal(s) across: {types_str}. "
        f"Weighted concern score: {score:.1f}/10 (Brignull-style taxonomy heuristics)."
    )


def detect_dark_patterns(
    text: str,
    bounding_boxes: list[dict] | None = None,
) -> DarkPatternReport:
    boxes = bounding_boxes or []
    collected: list[DarkPatternMatch] = []
    collected.extend(_detect_urgency(text))
    collected.extend(_detect_confirmshaming(text))
    collected.extend(_detect_pre_checked(text))
    collected.extend(_detect_hidden_costs(text))
    collected.extend(_detect_forced_continuity(text))
    collected.extend(_detect_misdirection(boxes))
    collected = _dedupe_matches(collected)
    collected = _drop_subsumed_evidence(collected)
    score = min(10.0, _compute_score(collected))
    summary = _build_summary(collected, score)
    return DarkPatternReport(patterns=collected, score=score, summary=summary)
