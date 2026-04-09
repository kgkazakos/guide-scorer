"""Parse raw discussion guide text into structured form."""
from __future__ import annotations

import re

from .models import ParsedGuide

# A line is a "probe" if it is explicitly labelled or deeply indented
_PROBE_PREFIX = re.compile(
    r"^\s*[-•*]?\s*(?:probe|follow[- ]?up|fp)\s*[:\-]?\s*",
    re.IGNORECASE,
)
_INDENTED = re.compile(r"^\s{3,}")

# A line contains a question if it has at least one question mark
# preceded by ≥5 characters of substance
_QUESTION_RE = re.compile(r".{5,}\?")

# Section header heuristics
_SECTION_RE = re.compile(
    r"^(?:"
    r"#{1,3}\s+.+"                                    # Markdown heading
    r"|[A-Z][A-Z\s/\-]{3,}(?:\s*\([^)]*\))?\s*:?\s*" # ALL CAPS label
    r"|(?:intro(?:duction)?|warm.?up|opening|background"
    r"|core|main|closing|close|wrap.?up|debrief"
    r"|section|part\s+\d+)\b.*"                       # named section
    r")$",
    re.IGNORECASE,
)

# Session length anywhere in the text
_SESSION_TIME_RE = re.compile(
    r"(?:session|interview|study)\s+(?:length|duration|time)\s*[:\-]?\s*(\d+)\s*min",
    re.IGNORECASE,
)
# Also catch bare "60 minutes" near guide headers
_BARE_TIME_RE = re.compile(
    r"\b(\d{2,3})[- ]?(?:minute|min)\b",
    re.IGNORECASE,
)


def parse_guide(text: str) -> ParsedGuide:
    """Return a :class:`ParsedGuide` from raw guide text."""
    lines = text.split("\n")

    all_questions: list[str] = []
    main_questions: list[str] = []
    probe_questions: list[str] = []
    section_headers: list[str] = []
    session_minutes: int | None = None

    # --- session duration ---
    m = _SESSION_TIME_RE.search(text)
    if m:
        session_minutes = int(m.group(1))
    else:
        # Look for bare duration hint in first 10 lines
        for line in lines[:10]:
            bm = _BARE_TIME_RE.search(line)
            if bm:
                candidate = int(bm.group(1))
                if 15 <= candidate <= 180:
                    session_minutes = candidate
                break

    # --- line-by-line pass ---
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Section header (no question mark, short enough)
        if (
            _SECTION_RE.match(stripped)
            and "?" not in stripped
            and len(stripped) <= 70
        ):
            section_headers.append(stripped)
            continue

        # Question line
        if _QUESTION_RE.search(stripped):
            all_questions.append(stripped)
            if _PROBE_PREFIX.match(line) or _INDENTED.match(line):
                probe_questions.append(stripped)
            else:
                main_questions.append(stripped)

    return ParsedGuide(
        raw_text=text,
        all_questions=all_questions,
        main_questions=main_questions,
        probe_questions=probe_questions,
        section_headers=section_headers,
        session_minutes=session_minutes,
        word_count=len(text.split()),
    )
