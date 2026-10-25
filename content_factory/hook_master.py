"""ULTIMATE ROBOT TEAM — content_factory/hook_master.py

Content Factory robot 3 of 20: the hook master — the قلاب specialist.

Writes the first-2-seconds hook for a concept: the exact line the
host speaks AND that appears as on-screen text. Produces 3 candidate
hooks and picks the strongest, so the hook_critic later judges the
best one, not the only one. Accepts fix notes from the quality
gatekeeper and rewrites against them (the retry loop).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import APPROVED_FACTS, fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the HOOK MASTER of a travel short-form team — the "
    "specialist in the first 2 seconds. Your hooks stop thumbs: "
    "curiosity gaps, bold honest claims, pattern interrupts. MAX 8 "
    "words per hook. Spoken by the host AND shown as on-screen text. "
    "Catchy but HONEST — the video must deliver on the hook. "
    + APPROVED_FACTS + " Reply with ONLY valid JSON, no other text."
)


def write_hooks(concept, location="", fix_notes=None):
    """Return {"ok": True, "hooks": [3], "best_hook":..., "best_why":...}.

    fix_notes: optional list of gatekeeper/critic notes the new hooks
    must fix (used by the orchestrator's one retry).
    """
    fix_block = ""
    if fix_notes:
        fix_block = ("The previous hook was REJECTED by the quality "
                     "gate. Fix exactly these problems:\n- "
                     + "\n- ".join(str(n) for n in fix_notes) + "\n")
    prompt = (
        f"Concept: {concept}\nLocation: {location}\n" + fix_block +
        "Write 3 DIFFERENT hooks for this video (one curiosity gap, "
        "one bold honest claim, one pattern interrupt). Each hook: "
        "MAX 8 words, understandable with the sound OFF (it is also "
        "the on-screen text), and the video must honestly deliver "
        "on it.\n"
        "Then pick the single strongest hook and say why in one "
        "sentence.\n"
        'Reply ONLY valid JSON: {"hooks": ["...", "...", "..."], '
        '"best_hook": "...", "best_why": "..."}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=600, temperature=0.9)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    hooks = [str(h).strip() for h in data.get("hooks", []) if str(h).strip()]
    best = str(data.get("best_hook", "")).strip()
    if len(hooks) < 2 or not best:
        return fail("AI returned incomplete hooks")
    if best not in hooks:
        hooks.insert(0, best)
    return {"ok": True, "ai_used": True, "hooks": hooks[:3],
            "best_hook": best,
            "best_why": str(data.get("best_why", "")).strip()}


HOOK_MASTER_ROBOT = {"write_hooks": write_hooks}
