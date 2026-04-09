"""Tests for guide_scorer.dimensions — all eight dimensions."""
from pathlib import Path

import pytest

from guide_scorer.dimensions import (
    score_neutrality,
    score_probe_depth,
    score_sequencing,
    score_coverage,
    score_time_realism,
    score_participant_framing,
    score_hypothesis_shielding,
    score_ethical_safety,
)
from guide_scorer.parser import parse_guide

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def parsed(name: str):
    return parse_guide(load(name))


# ---------------------------------------------------------------------------
# 1. Neutrality
# ---------------------------------------------------------------------------

class TestNeutrality:
    def test_good_guide_scores_high(self):
        result = score_neutrality(parsed("good_guide.txt"))
        assert result.score >= 75

    def test_poor_guide_scores_low(self):
        result = score_neutrality(parsed("poor_guide.txt"))
        assert result.score <= 50

    def test_leading_language_detected(self):
        text = "1. Don't you think this is obvious?\n2. Wouldn't you agree it's clear?"
        result = score_neutrality(parse_guide(text))
        assert result.score <= 70
        assert len(result.issues) >= 1

    def test_clean_guide_no_issues(self):
        text = "1. Tell me about your experience.\n2. What led you to that decision?"
        result = score_neutrality(parse_guide(text))
        assert result.issues == []

    def test_weight_is_020(self):
        result = score_neutrality(parsed("good_guide.txt"))
        assert result.weight == pytest.approx(0.20)

    def test_score_clamped_to_zero(self):
        # Many leading patterns → score should not go below 0
        lines = "\n".join(
            [f"{i+1}. Don't you think you should? Surely you agree it's obvious." for i in range(10)]
        )
        result = score_neutrality(parse_guide(lines))
        assert result.score >= 0


# ---------------------------------------------------------------------------
# 2. Probe Depth
# ---------------------------------------------------------------------------

class TestProbeDepth:
    def test_good_guide_scores_high(self):
        result = score_probe_depth(parsed("good_guide.txt"))
        assert result.score >= 65

    def test_poor_guide_scores_low(self):
        result = score_probe_depth(parsed("poor_guide.txt"))
        assert result.score <= 45

    def test_no_probes_penalised(self):
        text = "1. What do you think?\n2. How do you feel?"
        result = score_probe_depth(parse_guide(text))
        assert result.score <= 40

    def test_weight_is_015(self):
        result = score_probe_depth(parsed("good_guide.txt"))
        assert result.weight == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# 3. Sequencing
# ---------------------------------------------------------------------------

class TestSequencing:
    def test_good_guide_scores_high(self):
        result = score_sequencing(parsed("good_guide.txt"))
        assert result.score >= 70

    def test_poor_guide_scores_low(self):
        result = score_sequencing(parsed("poor_guide.txt"))
        assert result.score <= 40

    def test_no_warmup_penalised(self):
        text = (
            "CORE:\n"
            "1. Tell me about your job.\n"
            "CLOSING:\n"
            "2. Anything else?\n"
        )
        result = score_sequencing(parse_guide(text))
        assert any("warm" in i.lower() for i in result.issues)

    def test_no_closing_penalised(self):
        text = (
            "INTRO:\n1. How are you?\n"
            "WARM-UP:\n2. Tell me about yourself.\n"
            "CORE:\n3. What do you think?\n"
        )
        result = score_sequencing(parse_guide(text))
        assert any("clos" in i.lower() for i in result.issues)

    def test_weight_is_015(self):
        result = score_sequencing(parsed("good_guide.txt"))
        assert result.weight == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# 4. Coverage
# ---------------------------------------------------------------------------

class TestCoverage:
    def test_good_guide_scores_high(self):
        result = score_coverage(parsed("good_guide.txt"))
        assert result.score >= 70

    def test_minimal_guide_scores_low(self):
        result = score_coverage(parsed("minimal_guide.txt"))
        assert result.score <= 55

    def test_no_questions_scores_zero(self):
        result = score_coverage(parse_guide("No questions here."))
        assert result.score == 0

    def test_too_many_questions_penalised(self):
        lines = "\n".join([f"{i+1}. Question {i+1}?" for i in range(25)])
        result = score_coverage(parse_guide(lines))
        assert result.score <= 70

    def test_weight_is_010(self):
        result = score_coverage(parsed("good_guide.txt"))
        assert result.weight == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# 5. Time Realism
# ---------------------------------------------------------------------------

class TestTimeRealism:
    def test_good_guide_realistic(self):
        result = score_time_realism(parsed("good_guide.txt"))
        assert result.score >= 70

    def test_too_many_questions_penalised(self):
        lines = "Session Duration: 30 minutes\n"
        lines += "\n".join([f"{i+1}. Question {i+1}?" for i in range(20)])
        result = score_time_realism(parse_guide(lines))
        assert result.score <= 60

    def test_no_session_time_partial_score(self):
        text = "1. What do you think?\n2. How do you feel?\n3. Walk me through it?"
        result = score_time_realism(parse_guide(text))
        assert result.score > 0

    def test_weight_is_010(self):
        result = score_time_realism(parsed("good_guide.txt"))
        assert result.weight == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# 6. Participant Framing
# ---------------------------------------------------------------------------

class TestParticipantFraming:
    def test_good_guide_scores_high(self):
        result = score_participant_framing(parsed("good_guide.txt"))
        assert result.score >= 70

    def test_researcher_language_penalised(self):
        text = (
            "We want to know how you use our product.\n"
            "1. We think there's a problem. Do you agree?\n"
            "2. Our goal is to improve. How do you feel about our app?"
        )
        result = score_participant_framing(parse_guide(text))
        assert result.score <= 50
        assert len(result.issues) >= 1

    def test_weight_is_010(self):
        result = score_participant_framing(parsed("good_guide.txt"))
        assert result.weight == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# 7. Hypothesis Shielding
# ---------------------------------------------------------------------------

class TestHypothesisShielding:
    def test_good_guide_scores_high(self):
        result = score_hypothesis_shielding(parsed("good_guide.txt"))
        assert result.score >= 80

    def test_poor_guide_scores_low(self):
        result = score_hypothesis_shielding(parsed("poor_guide.txt"))
        assert result.score <= 60

    def test_exposed_hypothesis_detected(self):
        text = (
            "We believe that users struggle with onboarding.\n"
            "1. Have you experienced onboarding problems?"
        )
        result = score_hypothesis_shielding(parse_guide(text))
        assert result.score < 100
        assert len(result.issues) >= 1

    def test_weight_is_010(self):
        result = score_hypothesis_shielding(parsed("good_guide.txt"))
        assert result.weight == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# 8. Ethical Safety
# ---------------------------------------------------------------------------

class TestEthicalSafety:
    def test_good_guide_scores_high(self):
        result = score_ethical_safety(parsed("good_guide.txt"))
        assert result.score >= 50

    def test_poor_guide_scores_low(self):
        result = score_ethical_safety(parsed("poor_guide.txt"))
        assert result.score <= 20

    def test_consent_mention_boosts_score(self):
        text = "Participation is voluntary. You may withdraw at any time. This is confidential."
        result = score_ethical_safety(parse_guide(text))
        assert result.score >= 40

    def test_recording_mention_boosts_score(self):
        text = "We would like to record this session. Is that okay? 1. What do you think?"
        result = score_ethical_safety(parse_guide(text))
        assert result.score >= 15

    def test_weight_is_010(self):
        result = score_ethical_safety(parsed("good_guide.txt"))
        assert result.weight == pytest.approx(0.10)
