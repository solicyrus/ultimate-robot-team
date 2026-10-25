"""ULTIMATE ROBOT TEAM — content_factory/quality_gatekeeper.py

Content Factory robot 18 of 20: the quality gatekeeper.

THE RULE (Cyrus's decision, 2026-10-25): NO critic blocking.
People watch anything when the hook grabs and the title is
attractive — so the hook score NEVER blocks a package. The hook
critic only ranks candidates and advises; its score is recorded
in the package as information for the human approver, whose tap
is the only real gate.

The ONLY hard fail left is the fact scan (fact_critic's
deterministic scan — Cyrus's business honesty rule, not a
critic): a package carrying an invented price, hour, or phone
number is rejected, with the scan's flags as fix notes; the
orchestrator revises the flagged fields ONCE and re-checks. The
final score on a fact-clean package is simply the hook score,
recorded as-is. GATE_MIN (8.0) survives only as the "strong
hook" benchmark noted in advisory fix notes — it gates nothing.
"""

GATE_MIN = 8.0


def judge(hook_score, fact_result, hook_fix=""):
    """Combine the verdicts under the no-critic-blocking rule.

    hook_score: float 0-10 from hook_critic — INFORMATION ONLY.
    It is recorded as the final score and can never fail a
    package (the hook critic ranks and advises; Cyrus's approval
    tap is the only real gate).
    fact_result: fact_critic's dict {"passed": bool,
    "flags": [...]} — "passed" there means the deterministic
    fact scan found nothing. That scan is the ONLY hard fail:
    invented prices/hours/phones still block.
    Returns {"passed": bool, "final_score": float,
             "gate_min": 8.0, "fix_notes": [...]} — fix_notes on a
    pass are advisory notes for the human approver.
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
        notes.append(f"Advisory: hook scored {score:.1f}/10 "
                     f"(strong-hook benchmark {GATE_MIN:.0f}/10) "
                     "— recorded for the human approver; scores "
                     "no longer block.")
        if hook_fix and hook_fix.lower() != "none":
            notes.append(f"Hook critic's advice: {hook_fix}")
    return {"passed": True,
            "final_score": round(score, 1),
            "gate_min": GATE_MIN, "fix_notes": notes}


QUALITY_GATEKEEPER_ROBOT = {"judge": judge, "GATE_MIN": GATE_MIN}
