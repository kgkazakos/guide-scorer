"""Tests for guide_scorer.llm — mocked, no real API calls."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from guide_scorer.models import LLMBackend
from guide_scorer.scorer import GuideScorer

FIXTURES = Path(__file__).parent / "fixtures"
_scorer = GuideScorer()


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _base_result():
    return _scorer.score(load("good_guide.txt"))


# ---------------------------------------------------------------------------
# _resolve_key
# ---------------------------------------------------------------------------

class TestResolveKey:
    def test_explicit_key_returned(self):
        from guide_scorer.llm import _resolve_key
        assert _resolve_key(LLMBackend.OPENAI, "sk-test") == "sk-test"

    def test_env_key_used_when_no_explicit(self, monkeypatch):
        from guide_scorer.llm import _resolve_key
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        assert _resolve_key(LLMBackend.OPENAI, None) == "env-key"

    def test_raises_when_no_key(self, monkeypatch):
        from guide_scorer.llm import _resolve_key
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            _resolve_key(LLMBackend.OPENAI, None)

    def test_anthropic_env_var_name(self, monkeypatch):
        from guide_scorer.llm import _resolve_key
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-key")
        assert _resolve_key(LLMBackend.ANTHROPIC, None) == "ant-key"

    def test_gemini_env_var_name(self, monkeypatch):
        from guide_scorer.llm import _resolve_key
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-key")
        assert _resolve_key(LLMBackend.GEMINI, None) == "goog-key"


# ---------------------------------------------------------------------------
# _configure_dspy
# ---------------------------------------------------------------------------

class TestConfigureDspy:
    def test_raises_import_error_without_dspy(self, monkeypatch):
        """If dspy is not installed, a clean ImportError is raised."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "dspy":
                raise ImportError("No module named 'dspy'")
            return real_import(name, *args, **kwargs)

        from guide_scorer.llm import _configure_dspy
        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="guide-scorer\\[llm\\]"):
                _configure_dspy(LLMBackend.OPENAI, "sk-test")

    def test_configures_openai_model(self):
        from guide_scorer.llm import _MODELS
        assert _MODELS[LLMBackend.OPENAI] == "openai/gpt-4o-mini"

    def test_configures_anthropic_model(self):
        from guide_scorer.llm import _MODELS
        assert _MODELS[LLMBackend.ANTHROPIC] == "anthropic/claude-haiku-4-5-20251001"

    def test_configures_gemini_model(self):
        from guide_scorer.llm import _MODELS
        assert _MODELS[LLMBackend.GEMINI] == "gemini/gemini-2.0-flash"

    def test_all_backends_have_model(self):
        from guide_scorer.llm import _MODELS
        for backend in LLMBackend:
            assert backend in _MODELS

    def test_all_backends_have_env_key(self):
        from guide_scorer.llm import _ENV_KEYS
        for backend in LLMBackend:
            assert backend in _ENV_KEYS


# ---------------------------------------------------------------------------
# enrich_with_llm — mocked DSPy
# ---------------------------------------------------------------------------

def _make_dspy_mock():
    """Return a mock dspy module with ChainOfThought and configure stubs."""
    dspy_mock = MagicMock()

    # ChainOfThought(...) returns a callable predictor
    def make_predictor(*args, **kwargs):
        predictor = MagicMock()
        predictor.return_value = SimpleNamespace(
            rationale="Mock rationale text for this dimension.",
            narrative="Mock overall narrative for the guide.",
        )
        return predictor

    dspy_mock.ChainOfThought.side_effect = make_predictor
    dspy_mock.LM.return_value = MagicMock()
    dspy_mock.configure = MagicMock()

    # Signature base class
    class FakeSignature:
        pass

    dspy_mock.Signature = FakeSignature
    dspy_mock.InputField.return_value = None
    dspy_mock.OutputField.return_value = None

    return dspy_mock


class TestEnrichWithLlm:
    """Tests that enrich_with_llm wires correctly — DSPy calls are mocked."""

    def _run(self, backend: LLMBackend, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")

        result = _base_result()
        text = load("good_guide.txt")

        dspy_mock = _make_dspy_mock()

        with patch.dict("sys.modules", {"dspy": dspy_mock}):
            from guide_scorer import llm as llm_module
            # Reload to pick up patched sys.modules
            import importlib
            importlib.reload(llm_module)
            llm_module.enrich_with_llm(result, text, backend)

        return result

    def test_openai_populates_narrative(self, monkeypatch):
        result = self._run(LLMBackend.OPENAI, monkeypatch)
        assert result.narrative is not None
        assert len(result.narrative) > 0

    def test_anthropic_populates_narrative(self, monkeypatch):
        result = self._run(LLMBackend.ANTHROPIC, monkeypatch)
        assert result.narrative is not None

    def test_gemini_populates_narrative(self, monkeypatch):
        result = self._run(LLMBackend.GEMINI, monkeypatch)
        assert result.narrative is not None

    def test_all_dimensions_get_rationale(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")

        result = _base_result()
        text = load("good_guide.txt")
        dspy_mock = _make_dspy_mock()

        with patch.dict("sys.modules", {"dspy": dspy_mock}):
            import importlib
            from guide_scorer import llm as llm_module
            importlib.reload(llm_module)
            llm_module.enrich_with_llm(result, text, LLMBackend.OPENAI)

        populated = [d for d in result.dimensions if d.rationale is not None]
        assert len(populated) == 8

    def test_scores_unchanged_after_enrichment(self, monkeypatch):
        """LLM enrichment must never modify rule-based scores."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")

        result = _base_result()
        original_scores = [d.score for d in result.dimensions]
        original_overall = result.overall_score

        dspy_mock = _make_dspy_mock()

        with patch.dict("sys.modules", {"dspy": dspy_mock}):
            import importlib
            from guide_scorer import llm as llm_module
            importlib.reload(llm_module)
            llm_module.enrich_with_llm(result, load("good_guide.txt"), LLMBackend.OPENAI)

        assert [d.score for d in result.dimensions] == original_scores
        assert result.overall_score == original_overall

    def test_returns_result_for_chaining(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")

        result = _base_result()
        dspy_mock = _make_dspy_mock()

        with patch.dict("sys.modules", {"dspy": dspy_mock}):
            import importlib
            from guide_scorer import llm as llm_module
            importlib.reload(llm_module)
            returned = llm_module.enrich_with_llm(
                result, load("good_guide.txt"), LLMBackend.ANTHROPIC
            )

        assert returned is result

    def test_dspy_chain_of_thought_called(self, monkeypatch):
        """ChainOfThought should be used (not bare Predict)."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")

        result = _base_result()
        dspy_mock = _make_dspy_mock()

        with patch.dict("sys.modules", {"dspy": dspy_mock}):
            import importlib
            from guide_scorer import llm as llm_module
            importlib.reload(llm_module)
            llm_module.enrich_with_llm(result, load("good_guide.txt"), LLMBackend.OPENAI)

        assert dspy_mock.ChainOfThought.called

    def test_llm_failure_leaves_rationale_none(self, monkeypatch):
        """If the LM raises, rationale/narrative should be None, not crash."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")

        result = _base_result()

        dspy_mock = MagicMock()
        dspy_mock.LM.return_value = MagicMock()
        dspy_mock.configure = MagicMock()

        def make_failing_predictor(*args, **kwargs):
            predictor = MagicMock()
            predictor.side_effect = RuntimeError("API timeout")
            return predictor

        dspy_mock.ChainOfThought.side_effect = make_failing_predictor

        class FakeSignature:
            pass

        dspy_mock.Signature = FakeSignature
        dspy_mock.InputField.return_value = None
        dspy_mock.OutputField.return_value = None

        with patch.dict("sys.modules", {"dspy": dspy_mock}):
            import importlib
            from guide_scorer import llm as llm_module
            importlib.reload(llm_module)
            llm_module.enrich_with_llm(result, load("good_guide.txt"), LLMBackend.OPENAI)

        assert all(d.rationale is None for d in result.dimensions)
        assert result.narrative is None

    def test_no_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        result = _base_result()

        from guide_scorer.llm import enrich_with_llm
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            enrich_with_llm(result, load("good_guide.txt"), LLMBackend.ANTHROPIC)
