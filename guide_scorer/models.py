"""Data models for guide-scorer."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LLMBackend(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


@dataclass
class ParsedGuide:
    """Parsed representation of a discussion guide."""

    raw_text: str
    all_questions: list[str]
    main_questions: list[str]
    probe_questions: list[str]
    section_headers: list[str]
    session_minutes: Optional[int]
    word_count: int


@dataclass
class DimensionResult:
    """Result for a single scoring dimension."""

    name: str
    key: str
    score: float          # 0–100
    weight: float         # proportion of overall score
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    rationale: Optional[str] = None


@dataclass
class GuideScoreResult:
    """Full scoring result for a discussion guide."""

    overall_score: float
    grade: str
    dimensions: list[DimensionResult]
    question_count: int
    probe_count: int
    section_count: int
    session_minutes: Optional[int]
    narrative: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 1),
            "grade": self.grade,
            "question_count": self.question_count,
            "probe_count": self.probe_count,
            "section_count": self.section_count,
            "session_minutes": self.session_minutes,
            "narrative": self.narrative,
            "dimensions": [
                {
                    "name": d.name,
                    "key": d.key,
                    "score": round(d.score, 1),
                    "weight": d.weight,
                    "issues": d.issues,
                    "suggestions": d.suggestions,
                    "rationale": d.rationale,
                }
                for d in self.dimensions
            ],
        }


def letter_grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"
