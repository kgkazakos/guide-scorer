"""Basic usage example for guide-scorer."""
from guide_scorer import GuideScorer

guide_text = """
DISCUSSION GUIDE: Onboarding Experience
Session Length: 45 minutes

INTRODUCTION
Thank you for joining us. This is voluntary and confidential.
We'd like to record the session — is that okay? You can stop at any time.

WARM-UP
1. Tell me a bit about yourself and your role.
   Probe: How long have you been in this role?

CORE
2. Walk me through the first time you used the product.
   Probe: What were you trying to accomplish?
   Probe: What happened?

3. What did you find confusing or unclear during setup?
   Probe: How did you work around it?

4. What would have made those first few days easier?
   Probe: Can you give me a specific example?

CLOSING
5. Is there anything else you'd like to share?

Thank you for your time today.
"""

scorer = GuideScorer()
result = scorer.score(guide_text)

print(f"Overall Score : {result.overall_score:.1f}/100  (Grade: {result.grade})")
print(f"Questions     : {result.question_count}")
print(f"Probes        : {result.probe_count}")
print()

for dim in result.dimensions:
    bar = "█" * int(dim.score / 10) + "░" * (10 - int(dim.score / 10))
    print(f"{dim.name:<22} {bar}  {dim.score:.0f}/100")
    for issue in dim.issues:
        print(f"  ⚠  {issue}")

# --- JSON output ---
import json
data = result.to_dict()
print("\n--- JSON snippet ---")
print(json.dumps({
    "overall_score": data["overall_score"],
    "grade": data["grade"],
    "dimensions": [{"name": d["name"], "score": d["score"]} for d in data["dimensions"]]
}, indent=2))
