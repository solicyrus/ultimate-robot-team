"""ULTIMATE ROBOT TEAM — content_factory/hook_critic.py

Content Factory robot 16 of 20: the hook critic.

Scores ONE hook 0-10 for scroll-stopping strength, with reasons and
a concrete fix. This is a JUDGE, not a writer: it is deliberately
strict — most hooks are a 5-7; an 8+ must genuinely earn it
(specific, surprising or curiosity-loaded, understandable muted,
and honest against what the video delivers). Its score feeds the
quality gatekeeper.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the HOOK CRITIC of a travel short-form team — a strict, "
    "honest judge of first-2-seconds hooks. You have seen a million "
    "hooks; average ones bore you. You score what the hook EARNS, "
    "not what it tries. Reply with ONLY valid JSON, no other text."
)


def score_hook(hook, concept):
    """Return {"ok": True, "score": float 0-10, "reasons": [...],
    "fix": "..."} or an honest failure dict."""
    prompt = (
        f"Hook: \"{hook}\"\nThe video it opens: {concept}\n"
        "Score this hook 0-10 on scroll-stopping strength. Judge:\n"
        "- curiosity: does it open a question the viewer must close?\n"
        "- specificity: concrete words beat vague ones.\n"
        "- muted test: does it work as on-screen text with no sound?\n"
        "- honesty: can THIS video truly deliver on it?\n"
        "- length: 8 words or fewer is full marks; longer loses.\n"
        "Be strict: 5-7 is a normal working hook. 8+ is rare and "
        "must be truly sharp. 9-10 is exceptional.\n"
        "Give the score, 2-3 short reasons, and ONE concrete fix "
        "that would raise the score (or \"none\" if it is already "
        "excellent).\n"
        'Reply ONLY valid JSON: {"score": 7.5, "reasons": ["..."], '
        '"fix": "..."}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=500, temperature=0.35)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    try:
        score = float(data.get("score"))
    except (TypeError, ValueError):
        return fail("AI returned a non-numeric hook score")
    score = max(0.0, min(10.0, score))
    reasons = [str(r).strip() for r in data.get("reasons", [])
               if str(r).strip()]
    return {"ok": True, "ai_used": True, "score": score,
            "reasons": reasons[:3],
            "fix": str(data.get("fix", "")).strip()}


HOOK_CRITIC_ROBOT = {"score_hook": score_hook}
