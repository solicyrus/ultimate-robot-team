"""ULTIMATE ROBOT TEAM — content_factory/quality_gatekeeper.py

Content Factory robot 18 of 20: the quality gatekeeper — "only the
best" is enforced HERE, deterministically (no AI, no mood, no
favouritism).

The gate:
- Any fact-critic flag is an automatic fail (honesty is not scored,
  it is required), and the final score is capped at 3.0.
- Otherwise the final score is the hook critic's score.
- PASS requires final score >= GATE_MIN (8.0 / 10).

On a fail it returns concrete fix notes; the orchestrator feeds
them back to the hook master for ONE retry, then gives up honestly
and queues nothing.
"""

GATE_MIN = 8.0


def judge(hook_score, fact_result, hook_fix=""):
    """Combine the critics' verdicts.

    hook_score: float 0-10 from hook_critic.
    fact_result: fact_critic's dict {"passed": bool, "flags": [...]}.
    Returns {"passed": bool, "final_score": float,
             "gate_min": 8.0, "fix_notes": [...]}.
    """
    notes = []
    facts_ok = bool((fact_result or {}).get("passed"))
    try:
        score = float(hook_score)
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(10.0, score))
    if not facts_ok:
        for f in (fact_result or {}).get("flags", []):
            notes.append(f"FACT: {f}")
        notes.append("Remove every invented fact — only the "
                     "approved facts may be stated.")
        final = min(score, 3.0)
        return {"passed": False, "final_score": round(final, 1),
                "gate_min": GATE_MIN, "fix_notes": notes}
    if score < GATE_MIN:
        notes.append(f"Hook scored {score:.1f}/10 — the gate needs "
                     f"{GATE_MIN:.0f}/10 or higher.")
        if hook_fix and hook_fix.lower() != "none":
            notes.append(f"Hook critic's fix: {hook_fix}")
        notes.append("Sharpen the hook: more specific, stronger "
                     "curiosity gap, max 8 words, works muted.")
    return {"passed": score >= GATE_MIN,
            "final_score": round(score, 1),
            "gate_min": GATE_MIN, "fix_notes": notes}


QUALITY_GATEKEEPER_ROBOT = {"judge": judge, "GATE_MIN": GATE_MIN}
