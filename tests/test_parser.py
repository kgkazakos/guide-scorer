"""Tests for guide_scorer.parser."""
from pathlib import Path

import pytest

from guide_scorer.parser import parse_guide

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParseGoodGuide:
    def setup_method(self):
        self.guide = parse_guide(load("good_guide.txt"))

    def test_main_questions_detected(self):
        assert len(self.guide.main_questions) >= 7

    def test_probe_questions_detected(self):
        assert len(self.guide.probe_questions) >= 5

    def test_session_minutes_parsed(self):
        assert self.guide.session_minutes == 60

    def test_section_headers_detected(self):
        assert len(self.guide.section_headers) >= 2

    def test_word_count_positive(self):
        assert self.guide.word_count > 50

    def test_raw_text_preserved(self):
        assert "mobile banking" in self.guide.raw_text.lower()


class TestParsePoorGuide:
    def setup_method(self):
        self.guide = parse_guide(load("poor_guide.txt"))

    def test_main_questions_detected(self):
        assert len(self.guide.main_questions) >= 8

    def test_no_probes(self):
        assert len(self.guide.probe_questions) == 0

    def test_no_session_minutes(self):
        assert self.guide.session_minutes is None


class TestParseMinimalGuide:
    def setup_method(self):
        self.guide = parse_guide(load("minimal_guide.txt"))

    def test_questions_found(self):
        assert len(self.guide.all_questions) == 2

    def test_no_probes(self):
        assert self.guide.probe_questions == []

    def test_no_sections(self):
        assert self.guide.section_headers == []


class TestParseEdgeCases:
    def test_empty_text(self):
        guide = parse_guide("")
        assert guide.all_questions == []
        assert guide.main_questions == []
        assert guide.word_count == 0

    def test_no_questions(self):
        guide = parse_guide("This is a plain text document with no questions.")
        assert guide.all_questions == []

    def test_session_time_in_header(self):
        text = "Session Duration: 45 minutes\n\n1. How are you?"
        guide = parse_guide(text)
        assert guide.session_minutes == 45

    def test_probe_prefix_detection(self):
        text = "1. What do you think?\n   Probe: Can you say more?\n2. How do you feel?"
        guide = parse_guide(text)
        assert len(guide.probe_questions) >= 1

    def test_indented_question_as_probe(self):
        text = "1. Tell me about your experience.\n      - What happened next?\n2. How did that make you feel?"
        guide = parse_guide(text)
        assert len(guide.probe_questions) >= 1
