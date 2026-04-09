# guide-scorer

**Score discussion guides across 8 research quality dimensions — rule-based core, optional LLM narrative.**

Part of the [CPR Orbital Series](https://github.com/kgkazakos) — 40 open-source tools for AI-native product research infrastructure, shipping every Friday.

---

## The problem

You've written a discussion guide. You *think* it's solid. But:

- Are your questions actually neutral, or subtly leading?
- Do you have enough probes to get past surface answers?
- Is your session time realistic for the question count?
- Have you inadvertently exposed your hypothesis before the participant speaks?

Most guides ship without a systematic quality check. `guide-scorer` runs one in seconds.

---

## What it scores

| # | Dimension | Weight | What it checks |
|---|-----------|--------|---------------|
| 1 | **Neutrality** | 20% | Leading language, loaded words, presuppositions |
| 2 | **Probe Depth** | 15% | Follow-up probe density per main question |
| 3 | **Sequencing** | 15% | Warm-up → core → close structure |
| 4 | **Coverage** | 10% | Question count and breadth relative to objectives |
| 5 | **Time Realism** | 10% | Question count vs. stated session length |
| 6 | **Participant Framing** | 10% | Participant-centred vs. researcher-centred language |
| 7 | **Hypothesis Shielding** | 10% | Premature hypothesis or finding exposure |
| 8 | **Ethical Safety** | 10% | Consent, recording permission, opt-out, confidentiality |

Grades: **A** (≥85) · **B** (≥70) · **C** (≥55) · **D** (≥40) · **F** (<40)

---

## Install

```bash
pip install guide-scorer
```

With LLM enrichment (OpenAI / Anthropic / Gemini):

```bash
pip install "guide-scorer[llm]"
```

---

## Usage

### CLI — single guide

```bash
# Rule-based scoring (no API key needed)
guide-scorer score my_guide.txt

# With LLM narrative (DSPy backend)
guide-scorer score my_guide.txt --llm-backend anthropic
guide-scorer score my_guide.txt --llm-backend openai
guide-scorer score my_guide.txt --llm-backend gemini

# JSON output
guide-scorer score my_guide.txt --json
guide-scorer score my_guide.txt --json --output results.json
```

### CLI — batch scoring

```bash
# Score all .txt files in a directory
guide-scorer batch guides/

# Specific file pattern
guide-scorer batch guides/ --pattern "*.md"

# JSON summary
guide-scorer batch guides/ --json --output batch_results.json
```

### Python API

```python
from guide_scorer import GuideScorer

scorer = GuideScorer()
result = scorer.score(open("my_guide.txt").read())

print(f"Score: {result.overall_score:.1f}/100  Grade: {result.grade}")

for dim in result.dimensions:
    print(f"  {dim.name}: {dim.score:.0f}")
    for issue in dim.issues:
        print(f"    ⚠ {issue}")

# JSON-serialisable dict
data = result.to_dict()
```

### With LLM enrichment

```python
from guide_scorer import GuideScorer, LLMBackend
from guide_scorer.llm import enrich_with_llm
import os

os.environ["ANTHROPIC_API_KEY"] = "..."

scorer = GuideScorer()
result = scorer.score(open("my_guide.txt").read())
enrich_with_llm(result, open("my_guide.txt").read(), LLMBackend.ANTHROPIC)

print(result.narrative)
for dim in result.dimensions:
    print(f"{dim.name}: {dim.rationale}")
```

---

## LLM backends

| Backend | Flag | Env var | Model |
|---------|------|---------|-------|
| Anthropic | `--llm-backend anthropic` | `ANTHROPIC_API_KEY` | `claude-haiku-4-5-20251001` |
| OpenAI | `--llm-backend openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Gemini | `--llm-backend gemini` | `GOOGLE_API_KEY` | `gemini-3.1-pro-preview` |

LLM backends are entirely optional. The rule-based core works with zero API calls. Use `--llm-backend` only when you want per-dimension expert rationale and an overall narrative.

---

## JSON output schema

```json
{
  "overall_score": 74.5,
  "grade": "B",
  "question_count": 9,
  "probe_count": 7,
  "section_count": 4,
  "session_minutes": 60,
  "narrative": "...",
  "dimensions": [
    {
      "name": "Neutrality",
      "key": "neutrality",
      "score": 85.0,
      "weight": 0.2,
      "issues": [],
      "suggestions": ["Questions appear neutral..."],
      "rationale": null
    }
  ]
}
```

---

## CI integration

```yaml
- name: Score discussion guides
  run: |
    pip install guide-scorer
    guide-scorer batch guides/ --json --output guide_scores.json
```

---

## Part of the CPR Ecosystem

`guide-scorer` is **Tool 7** in the [CPR Orbital Series](https://github.com/kgkazakos).

Related tools:

| Tool | What it does |
|------|-------------|
| [`qual-sniffer`](https://github.com/kgkazakos/qual-sniffer) | Detects methodological weaknesses in research plans |
| [`uxr-prompt-pack`](https://github.com/kgkazakos/uxr-prompt-pack) | Versioned LLM prompt library for UX research |
| [`survey-cleaner`](https://github.com/kgkazakos/survey-cleaner) | Removes speeders and gibberish from survey exports |
| [`insight-differ`](https://github.com/kgkazakos/insight-differ) | Compares research reports for contradictions and gaps |

**Computational Product Research (CPR)** is an emerging discipline combining rigorous quantitative and qualitative methods with LLM augmentation for product research workflows.

---

## Licence

MIT — see [LICENSE](LICENSE).
