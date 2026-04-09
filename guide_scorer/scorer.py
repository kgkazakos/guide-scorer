"""Main scoring orchestrator for guide-scorer."""
from __future__ import annotations

from .dimensions import DIMENSION_SCORERS
from .models import GuideScoreResult, letter_grade
from .parser import parse_guide


class GuideScorer:
    """Score a discussion guide across eight research quality dimensions."""

    def score(self, text: str) -> GuideScoreResult:
        """Run rule-based scoring on *text* and return a :class:`GuideScoreResult`."""
        guide = parse_guide(text)

        dimensions = [fn(guide) for fn in DIMENSION_SCORERS]

        overall = sum(d.score * d.weight for d in dimensions)

        return GuideScoreResult(
            overall_score=overall,
            grade=letter_grade(overall),
            dimensions=dimensions,
            question_count=len(guide.main_questions),
            probe_count=len(guide.probe_questions),
            section_count=len(guide.section_headers),
            session_minutes=guide.session_minutes,
        )
