"""Integration tests for GuideScorer and model layer."""
from pathlib import Path

import pytest

from guide_scorer.models import letter_grade, GuideScoreResult
from guide_scorer.scorer import GuideScorer

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# letter_grade helper
# ---------------------------------------------------------------------------

class TestLetterGrade:
    def test_a(self):
        assert letter_grade(90) == "A"

    def test_b(self):
        assert letter_grade(75) == "B"

    def test_c(self):
        assert letter_grade(60) == "C"

    def test_d(self):
        assert letter_grade(45) == "D"

    def test_f(self):
        assert letter_grade(30) == "F"

    def test_boundary_85(self):
        assert letter_grade(85) == "A"

    def test_boundary_70(self):
        assert letter_grade(70) == "B"


# ---------------------------------------------------------------------------
# GuideScorer
# ---------------------------------------------------------------------------

class TestGuideScorer:
    def setup_method(self):
        self.scorer = GuideScorer()

    def test_good_guide_high_score(self):
        result = self.scorer.score(load("good_guide.txt"))
        assert result.overall_score >= 60

    def test_poor_guide_low_score(self):
        result = self.scorer.score(load("poor_guide.txt"))
        assert result.overall_score <= 55

    def test_good_beats_poor(self):
        good = self.scorer.score(load("good_guide.txt"))
        poor = self.scorer.score(load("poor_guide.txt"))
        assert good.overall_score > poor.overall_score

    def test_returns_eight_dimensions(self):
        result = self.scorer.score(load("good_guide.txt"))
        assert len(result.dimensions) == 8

    def test_dimension_keys_unique(self):
        result = self.scorer.score(load("good_guide.txt"))
        keys = [d.key for d in result.dimensions]
        assert len(keys) == len(set(keys))

    def test_weights_sum_to_one(self):
        result = self.scorer.score(load("good_guide.txt"))
        total = sum(d.weight for d in result.dimensions)
        assert total == pytest.approx(1.0)

    def test_overall_within_bounds(self):
        result = self.scorer.score(load("good_guide.txt"))
        assert 0 <= result.overall_score <= 100

    def test_empty_guide(self):
        result = self.scorer.score("")
        assert result.overall_score >= 0
        assert result.grade in {"A", "B", "C", "D", "F"}

    def test_narrative_none_without_llm(self):
        result = self.scorer.score(load("good_guide.txt"))
        assert result.narrative is None

    def test_to_dict_structure(self):
        result = self.scorer.score(load("good_guide.txt"))
        d = result.to_dict()
        assert "overall_score" in d
        assert "grade" in d
        assert "dimensions" in d
        assert isinstance(d["dimensions"], list)
        assert len(d["dimensions"]) == 8

    def test_to_dict_dimension_keys(self):
        result = self.scorer.score(load("good_guide.txt"))
        for dim_dict in result.to_dict()["dimensions"]:
            assert "name" in dim_dict
            assert "score" in dim_dict
            assert "issues" in dim_dict
            assert "suggestions" in dim_dict

    def test_question_count_reported(self):
        result = self.scorer.score(load("good_guide.txt"))
        assert result.question_count >= 5

    def test_probe_count_good_guide(self):
        result = self.scorer.score(load("good_guide.txt"))
        assert result.probe_count >= 3
