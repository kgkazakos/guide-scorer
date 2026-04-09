"""guide-scorer — Score discussion guides across 8 research quality dimensions."""

__version__ = "0.1.0"

from .models import DimensionResult, GuideScoreResult, LLMBackend
from .parser import parse_guide
from .scorer import GuideScorer

__all__ = [
    "GuideScorer",
    "GuideScoreResult",
    "DimensionResult",
    "LLMBackend",
    "parse_guide",
    "__version__",
]
