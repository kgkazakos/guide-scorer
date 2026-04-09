"""LLM enrichment for guide-scorer via DSPy.

Supported backends: openai | anthropic | gemini
API keys read from environment:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY

Install extras:
  pip install "guide-scorer[llm]"
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from .models import GuideScoreResult, LLMBackend

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend configuration
# ---------------------------------------------------------------------------

# LiteLLM model identifiers used by DSPy
_MODELS: dict[str, str] = {
    LLMBackend.OPENAI: "openai/gpt-4o-mini",
    LLMBackend.ANTHROPIC: "anthropic/claude-haiku-4-5-20251001",
    LLMBackend.GEMINI: "gemini/gemini-2.0-flash",
}

_ENV_KEYS: dict[str, str] = {
    LLMBackend.OPENAI: "OPENAI_API_KEY",
    LLMBackend.ANTHROPIC: "ANTHROPIC_API_KEY",
    LLMBackend.GEMINI: "GOOGLE_API_KEY",
}


def _resolve_key(backend: LLMBackend, api_key: Optional[str]) -> str:
    if api_key:
        return api_key
    env = _ENV_KEYS[backend]
    key = os.getenv(env, "")
    if not key:
        raise ValueError(
            f"No API key for {backend.value}. "
            f"Set {env} or pass --api-key."
        )
    return key


def _configure_dspy(backend: LLMBackend, api_key: str) -> None:
    """Import and configure DSPy with the chosen backend LM."""
    try:
        import dspy  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "DSPy is required for LLM enrichment. "
            "Install with:  pip install 'guide-scorer[llm]'"
        ) from exc

    model_id = _MODELS[backend]

    # Gemini uses GOOGLE_API_KEY via LiteLLM — pass as api_key
    lm = dspy.LM(
        model=model_id,
        api_key=api_key,
        max_tokens=512,
        temperature=0.3,       # low variance for analytical rationale
    )
    dspy.configure(lm=lm)
    log.debug("DSPy configured: model=%s", model_id)


# ---------------------------------------------------------------------------
# DSPy Signatures
# ---------------------------------------------------------------------------

def _build_signatures():
    """Build DSPy Signature classes (lazy import keeps DSPy optional)."""
    import dspy  # type: ignore

    class ScoreDimension(dspy.Signature):
        """You are an expert UX research methodologist.
        Given a discussion guide excerpt and one scoring dimension's rule-based result,
        write a concise expert rationale that explains the score and names
        the single most actionable improvement a researcher could make right now."""

        dimension_name: str = dspy.InputField(
            desc="The quality dimension being evaluated (e.g. Neutrality, Probe Depth)"
        )
        score: float = dspy.InputField(
            desc="Rule-based score for this dimension, 0-100"
        )
        issues: str = dspy.InputField(
            desc="Issues detected by the rule-based engine; 'None' if clean"
        )
        guide_excerpt: str = dspy.InputField(
            desc="First 800 characters of the discussion guide under review"
        )
        rationale: str = dspy.OutputField(
            desc=(
                "2-3 sentences: (1) explain why the score makes sense given the issues, "
                "(2) name one concrete, specific action the researcher should take next"
            )
        )

    class NarrateResult(dspy.Signature):
        """You are an expert UX research methodologist.
        Given the overall scoring summary of a discussion guide,
        write a concise plain-English quality narrative for the researcher."""

        overall_score: float = dspy.InputField(desc="Overall weighted score, 0-100")
        grade: str = dspy.InputField(desc="Letter grade A-F")
        strongest_dimension: str = dspy.InputField(
            desc="The dimension with the highest score"
        )
        weakest_dimension: str = dspy.InputField(
            desc="The dimension with the lowest score"
        )
        question_count: int = dspy.InputField(
            desc="Number of main questions in the guide"
        )
        session_minutes: str = dspy.InputField(
            desc="Stated session length in minutes, or 'not specified'"
        )
        narrative: str = dspy.OutputField(
            desc=(
                "3 sentences: (1) overall quality verdict, "
                "(2) the guide's biggest strength, "
                "(3) the single most important improvement to make before going into field"
            )
        )

    return ScoreDimension, NarrateResult


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_with_llm(
    result: GuideScoreResult,
    raw_text: str,
    backend: LLMBackend,
    api_key: Optional[str] = None,
) -> GuideScoreResult:
    """Add DSPy-generated rationale and narrative to a :class:`GuideScoreResult`.

    Mutates *result* in place and returns it for chaining.
    The rule-based scores are never modified — only ``rationale`` and
    ``narrative`` fields are populated.

    Args:
        result:    Completed rule-based scoring result.
        raw_text:  Original guide text (used as context for the LM).
        backend:   Which LM backend to use (openai | anthropic | gemini).
        api_key:   Optional explicit API key; falls back to environment variable.

    Returns:
        The same *result* object, now with LLM-generated text fields populated.
    """
    key = _resolve_key(backend, api_key)
    _configure_dspy(backend, key)

    import dspy  # type: ignore — confirmed present after _configure_dspy

    ScoreDimension, NarrateResult = _build_signatures()

    # ChainOfThought gives better-reasoned rationale than bare Predict
    rate = dspy.ChainOfThought(ScoreDimension)
    narrate = dspy.ChainOfThought(NarrateResult)

    excerpt = raw_text[:800]

    # --- Per-dimension rationale ---
    for dim in result.dimensions:
        issues_str = "; ".join(dim.issues) if dim.issues else "None"
        try:
            pred = rate(
                dimension_name=dim.name,
                score=dim.score,
                issues=issues_str,
                guide_excerpt=excerpt,
            )
            dim.rationale = pred.rationale.strip()
        except Exception as exc:
            log.warning("LLM rationale failed for %s: %s", dim.name, exc)
            dim.rationale = None

    # --- Overall narrative ---
    sorted_dims = sorted(result.dimensions, key=lambda d: d.score)
    weakest = sorted_dims[0].name if sorted_dims else "unknown"
    strongest = sorted_dims[-1].name if sorted_dims else "unknown"
    session_str = (
        f"{result.session_minutes} min" if result.session_minutes else "not specified"
    )

    try:
        pred = narrate(
            overall_score=result.overall_score,
            grade=result.grade,
            strongest_dimension=strongest,
            weakest_dimension=weakest,
            question_count=result.question_count,
            session_minutes=session_str,
        )
        result.narrative = pred.narrative.strip()
    except Exception as exc:
        log.warning("LLM narrative failed: %s", exc)
        result.narrative = None

    return result
