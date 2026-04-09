"""Eight research quality dimensions for discussion guide scoring."""
from __future__ import annotations

import re

from .models import DimensionResult, ParsedGuide

# ---------------------------------------------------------------------------
# Shared patterns
# ---------------------------------------------------------------------------

_LEADING = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"don'?t you (?:think|agree|feel|believe)",
        r"wouldn'?t you (?:say|agree|think)",
        r"isn'?t it (?:true|fair|right|obvious)",
        r"don'?t you find",
        r"surely you",
        r"obviously[,\s]",
        r"clearly[,\s]",
        r"you (?:must|must have|have to|need to)\b",
        r"why (?:don'?t|didn'?t|haven'?t|aren'?t) you",
        r"as you (?:know|can see|probably know)",
        r"you (?:already|probably|obviously)",
    ]
]

_LOADED = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bfrustrat(?:ing|ed|ion)\b",
        r"\bannoy(?:ing|ed|ance)\b",
        r"\bterrible\b",
        r"\bawful\b",
        r"\bhorrible\b",
        r"\bpathetic\b",
    ]
]

_PROBE_MARKERS = [
    "tell me more",
    "can you elaborate",
    "elaborate on",
    "can you explain",
    "what do you mean",
    "how so",
    "walk me through",
    "say more",
    "what makes you say",
    "in what way",
    "give me an example",
    "could you give",
    "can you give",
    "what led",
    "can you describe",
    "what happened",
    "why is that",
]

_WARMUP_TERMS = re.compile(
    r"(?:intro(?:duction)?|warm[- ]?up|opening|background|getting started|"
    r"to start|to begin|before we dive)",
    re.IGNORECASE,
)
_CLOSING_TERMS = re.compile(
    r"(?:clos(?:e|ing)|wrap[- ]?up|debrief|final|last question|anything else|"
    r"to close|in closing|thank you)",
    re.IGNORECASE,
)

_RESEARCHER_CENTERED = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"we (?:want|need) to know",
        r"we'?re trying to",
        r"our (?:product|feature|app|tool|goal|team|hypothesis)",
        r"we (?:built|designed|created|think|believe|assume|expect)",
        r"our data (?:shows|suggests|indicates)",
    ]
]

_HYPOTHESIS_EXPOSURE = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"we (?:think|believe|expect|hypothes[ie]z[e]|assume) that",
        r"research (?:shows|suggests|indicates) that",
        r"our data shows",
        r"studies (?:show|suggest)",
        r"we (?:found|discovered) that",
        r"we'?ve heard that",
        r"most (?:users|people|participants) (?:struggle|find it hard|complain)",
    ]
]

_CONSENT_MARKERS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bconsent\b",
        r"record(?:ing)?\b",
        r"withdraw\b",
        r"opt[- ]out\b",
        r"stop at any time",
        r"leave at any time",
        r"\bconfidential\b",
        r"\banonymous\b",
        r"privacy\b",
        r"voluntary\b",
    ]
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _count_pattern_hits(patterns: list[re.Pattern], texts: list[str]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        for text in texts:
            m = pattern.search(text)
            if m:
                start = max(0, m.start() - 10)
                snippet = text[start : m.start() + 70].replace("\n", " ").strip()
                hits.append(snippet)
    return hits


# ---------------------------------------------------------------------------
# 1. Neutrality  (weight 0.20)
# ---------------------------------------------------------------------------

def score_neutrality(guide: ParsedGuide) -> DimensionResult:
    score = 100.0
    issues: list[str] = []
    suggestions: list[str] = []

    leading_hits = _count_pattern_hits(_LEADING, guide.all_questions)
    loaded_hits = _count_pattern_hits(_LOADED, guide.all_questions)

    for hit in leading_hits:
        score -= 15
        issues.append("Leading language detected: '" + hit[:60] + "...'")
    for hit in loaded_hits:
        score -= 8
        issues.append("Loaded/emotive word in question: '" + hit[:60] + "...'")

    if leading_hits:
        suggestions.append(
            "Reframe leading questions to open-ended forms, e.g. 'What is your view on...' "
            "instead of 'Don't you think...'"
        )
    if loaded_hits:
        suggestions.append(
            "Replace emotive adjectives with neutral language; let participants supply their "
            "own emotional framing."
        )
    if not issues:
        suggestions.append("Questions appear neutral -- good use of open-ended language.")

    return DimensionResult(
        name="Neutrality",
        key="neutrality",
        score=_clamp(score),
        weight=0.20,
        issues=issues,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# 2. Probe Depth  (weight 0.15)
# ---------------------------------------------------------------------------

def score_probe_depth(guide: ParsedGuide) -> DimensionResult:
    issues: list[str] = []
    suggestions: list[str] = []

    n_main = len(guide.main_questions)
    n_probe = len(guide.probe_questions)

    probe_text = " ".join(guide.raw_text.lower().split())
    marker_hits = sum(1 for m in _PROBE_MARKERS if m in probe_text)

    effective_probes = max(n_probe, marker_hits)
    ratio = effective_probes / n_main if n_main > 0 else 0

    if ratio == 0:
        score = 15.0
        issues.append("No follow-up probes detected -- guides without probes risk shallow answers.")
        suggestions.append(
            "Add at least 1-2 probes per main question: 'Can you say more about that?' "
            "or 'Walk me through what happened next.'"
        )
    elif ratio < 0.5:
        score = 40.0
        issues.append(
            f"Low probe density ({effective_probes} probes for {n_main} main questions). "
            "Aim for at least 1 probe per question."
        )
        suggestions.append("Add probes to your most critical questions to encourage richer responses.")
    elif ratio < 1.0:
        score = 65.0
        issues.append("Moderate probe depth -- some questions lack follow-ups.")
        suggestions.append("Add probes to any question exploring a core research topic.")
    elif ratio < 2.0:
        score = 85.0
        suggestions.append("Good probe coverage. Consider adding probes to emotionally significant moments.")
    else:
        score = 100.0
        suggestions.append("Strong probe depth across the guide.")

    return DimensionResult(
        name="Probe Depth",
        key="probe_depth",
        score=score,
        weight=0.15,
        issues=issues,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# 3. Sequencing  (weight 0.15)
# ---------------------------------------------------------------------------

def score_sequencing(guide: ParsedGuide) -> DimensionResult:
    score = 30.0
    issues: list[str] = []
    suggestions: list[str] = []

    header_text = " ".join(guide.section_headers).lower()
    full_lower = guide.raw_text.lower()

    has_warmup = bool(
        _WARMUP_TERMS.search(header_text) or _WARMUP_TERMS.search(full_lower[:300])
    )
    has_closing = bool(
        _CLOSING_TERMS.search(header_text) or _CLOSING_TERMS.search(full_lower[-400:])
    )
    has_sections = len(guide.section_headers) >= 2

    if has_warmup:
        score += 30
    else:
        issues.append("No warm-up section detected. Opening cold risks rapport problems.")
        suggestions.append(
            "Add a warm-up section (2-3 background questions) before core topics to "
            "build rapport and reduce participant anxiety."
        )

    if has_closing:
        score += 25
    else:
        issues.append("No closing/wrap-up section detected.")
        suggestions.append(
            "Add a closing section: ask 'Is there anything else you would like to share?' "
            "and thank the participant."
        )

    if has_sections:
        score += 15
    else:
        issues.append("Guide lacks clear section structure.")
        suggestions.append("Divide your guide into labelled sections (Intro, Core, Close) for clarity.")

    if not issues:
        suggestions.append("Good three-part structure: warm-up -> core -> close.")

    return DimensionResult(
        name="Sequencing",
        key="sequencing",
        score=_clamp(score),
        weight=0.15,
        issues=issues,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# 4. Coverage  (weight 0.10)
# ---------------------------------------------------------------------------

def score_coverage(guide: ParsedGuide) -> DimensionResult:
    issues: list[str] = []
    suggestions: list[str] = []

    n = len(guide.main_questions)

    if n == 0:
        score = 0.0
        issues.append("No main questions found in the guide.")
        suggestions.append("Add structured questions to the guide.")
    elif n < 3:
        score = 25.0
        issues.append(f"Only {n} main question(s) detected -- guide may lack breadth.")
        suggestions.append("Add more questions to cover your research objectives fully.")
    elif n < 6:
        score = 55.0
        issues.append(f"{n} main questions -- adequate for a short session but may miss topics.")
        suggestions.append(
            "Review your research objectives and ensure each one maps to at least one question."
        )
    elif n <= 12:
        score = 90.0
        suggestions.append(f"{n} main questions -- good coverage for a standard 60-min session.")
    elif n <= 18:
        score = 75.0
        issues.append(f"{n} questions is ambitious -- ensure time allows for depth, not just breadth.")
        suggestions.append(
            "Prioritise your questions and mark 3-4 as 'must ask' vs 'nice to have'."
        )
    else:
        score = 40.0
        issues.append(f"{n} questions is very high -- depth will be sacrificed for coverage.")
        suggestions.append("Cut to 15 or fewer main questions; depth beats breadth in qualitative research.")

    if guide.main_questions:
        words = [w.lower() for q in guide.main_questions for w in q.split() if len(w) > 4]
        unique_ratio = len(set(words)) / len(words) if words else 0
        if unique_ratio > 0.7 and n >= 5:
            score = min(100, score + 10)

    return DimensionResult(
        name="Coverage",
        key="coverage",
        score=_clamp(score),
        weight=0.10,
        issues=issues,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# 5. Time Realism  (weight 0.10)
# ---------------------------------------------------------------------------

def score_time_realism(guide: ParsedGuide) -> DimensionResult:
    issues: list[str] = []
    suggestions: list[str] = []

    n = len(guide.main_questions)
    mins = guide.session_minutes

    if mins is not None:
        expected = mins / 4
        ratio = n / expected if expected > 0 else 0

        if ratio < 0.4:
            score = 55.0
            issues.append(
                f"{n} questions for {mins} min -- guide may be too sparse "
                f"(expected ~{int(expected)})."
            )
            suggestions.append("Add questions or probes to fill the session productively.")
        elif ratio <= 1.3:
            score = 100.0
            suggestions.append(f"{n} questions fits comfortably within {mins} minutes.")
        elif ratio <= 1.8:
            score = 65.0
            issues.append(
                f"{n} questions may be tight for {mins} min (expected ~{int(expected)})."
            )
            suggestions.append(
                "Mark 2-3 questions as optional so you can cut if time runs short."
            )
        else:
            score = 30.0
            issues.append(
                f"{n} questions is too many for {mins} min (expected ~{int(expected)})."
            )
            suggestions.append(
                "Reduce question count significantly or extend the session. "
                "Rushing through questions harms data quality."
            )
    else:
        if n == 0:
            score = 20.0
            issues.append("No questions detected.")
        elif n < 4:
            score = 55.0
            issues.append("Very few questions -- session may feel too short.")
        elif n <= 15:
            score = 80.0
            suggestions.append(
                "Consider adding a session length note to the guide header for "
                "interviewer reference."
            )
        else:
            score = 60.0
            issues.append(f"{n} questions without a stated session length -- risk of overrun.")
            suggestions.append("Add a session duration header and mark optional questions.")

    return DimensionResult(
        name="Time Realism",
        key="time_realism",
        score=_clamp(score),
        weight=0.10,
        issues=issues,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# 6. Participant Framing  (weight 0.10)
# ---------------------------------------------------------------------------

def score_participant_framing(guide: ParsedGuide) -> DimensionResult:
    score = 100.0
    issues: list[str] = []
    suggestions: list[str] = []

    rc_hits = _count_pattern_hits(_RESEARCHER_CENTERED, [guide.raw_text])

    for hit in rc_hits:
        score -= 18
        issues.append("Researcher-centred language: '" + hit[:70] + "...'")

    if rc_hits:
        suggestions.append(
            "Remove phrases like 'we want to know' or 'our product' -- "
            "centre questions on the participant's experience."
        )
    else:
        you_count = len(re.findall(r"\byou\b", guide.raw_text, re.IGNORECASE))
        if you_count >= len(guide.main_questions):
            suggestions.append(
                "Good participant-centred framing -- questions consistently address "
                "the participant's own experience."
            )
        else:
            score = max(score - 10, 0)
            issues.append("Some questions may not be clearly anchored to the participant's experience.")
            suggestions.append(
                "Ensure each question is framed from the participant's perspective: "
                "'Tell me about a time you...' rather than abstract or general phrasing."
            )

    return DimensionResult(
        name="Participant Framing",
        key="participant_framing",
        score=_clamp(score),
        weight=0.10,
        issues=issues,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# 7. Hypothesis Shielding  (weight 0.10)
# ---------------------------------------------------------------------------

def score_hypothesis_shielding(guide: ParsedGuide) -> DimensionResult:
    score = 100.0
    issues: list[str] = []
    suggestions: list[str] = []

    hits = _count_pattern_hits(_HYPOTHESIS_EXPOSURE, [guide.raw_text])

    for hit in hits:
        score -= 22
        issues.append("Hypothesis exposed: '" + hit[:70] + "...'")

    if hits:
        suggestions.append(
            "Move hypothesis-revealing statements to a debrief section or researcher "
            "notes. Expose hypotheses only after the participant has shared their unprompted view."
        )
    else:
        suggestions.append("No premature hypothesis exposure detected -- good epistemic hygiene.")

    return DimensionResult(
        name="Hypothesis Shielding",
        key="hypothesis_shielding",
        score=_clamp(score),
        weight=0.10,
        issues=issues,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# 8. Ethical Safety  (weight 0.10)
# ---------------------------------------------------------------------------

def score_ethical_safety(guide: ParsedGuide) -> DimensionResult:
    score = 0.0
    issues: list[str] = []
    suggestions: list[str] = []

    full_lower = guide.raw_text.lower()
    found: list[str] = []

    marker_scores = {
        "consent": (20, "consent"),
        "record": (15, "recording permission"),
        r"withdraw|opt.out|stop at any time|leave at any time": (25, "opt-out/withdrawal option"),
        r"confidential|anonymous": (20, "confidentiality assurance"),
        "voluntary": (10, "voluntary participation statement"),
        "privacy": (10, "privacy mention"),
    }

    for pattern, (pts, label) in marker_scores.items():
        if re.search(pattern, full_lower):
            score += pts
            found.append(label)

    missing = [label for _, (_, label) in marker_scores.items() if label not in found]

    if not found:
        issues.append("No ethical safeguards detected in the guide.")
        suggestions.append(
            "Add an introductory section covering: consent, recording permission, "
            "confidentiality, and the participant's right to withdraw at any time."
        )
    else:
        if len(found) < 3:
            issues.append(
                f"Partial ethical coverage -- found: {', '.join(found)}. "
                f"Missing: {', '.join(missing)}."
            )
            suggestions.append(
                "Strengthen the preamble to include all key ethical elements before "
                "beginning the substantive questions."
            )
        else:
            suggestions.append(f"Good ethical framing -- covers: {', '.join(found)}.")

    return DimensionResult(
        name="Ethical Safety",
        key="ethical_safety",
        score=_clamp(score),
        weight=0.10,
        issues=issues,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------

DIMENSION_SCORERS = [
    score_neutrality,
    score_probe_depth,
    score_sequencing,
    score_coverage,
    score_time_realism,
    score_participant_framing,
    score_hypothesis_shielding,
    score_ethical_safety,
]
