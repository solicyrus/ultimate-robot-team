"""ULTIMATE ROBOT TEAM — content_factory/hook_master.py

Content Factory robot 3 of 20: the hook master — the قلاب specialist.

Writes the first-2-seconds hook for a concept: the exact line the
host speaks AND that appears as on-screen text. Two modes:

- write_hooks: 3 candidate hooks, self-picked best (the revision
  loop's quick rewrite).
- write_hook_candidates: the MULTI-CANDIDATE mode — 5 hooks, one
  per named formula (curiosity gap, bold honest claim, question,
  number/specific detail, contrast). The hook critic batch-scores
  them and the orchestrator runs with the best scorer, so the
  package never lives or dies on a single generic try.

Accepts fix notes from the quality gatekeeper and rewrites against
them (the retry loop).
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


# The five named formulas of the multi-candidate mode — every batch
# carries exactly one hook per formula, so the five tries attack the
# scroll from five genuinely different angles.
HOOK_FORMULAS = (
    ("curiosity_gap",
     "CURIOSITY GAP — open a question the viewer must stay to "
     "close (e.g. 'Nobody talks about…', 'What nobody tells you…')"),
    ("bold_claim",
     "BOLD HONEST CLAIM — a strong, specific claim this video can "
     "truly deliver on"),
    ("question",
     "QUESTION HOOK — ask the viewer a direct question they "
     "cannot help answering in their head"),
    ("number_detail",
     "NUMBER / SPECIFIC DETAIL — lead with a concrete number or "
     "one vivid specific detail (never an invented fact: no made-up "
     "prices, hours, distances or statistics)"),
    ("contrast",
     "CONTRAST HOOK — expectation vs reality, or Canada vs USA: "
     "two worlds colliding in one line"),
)

_FORMULA_ALIASES = {
    "curiosity_gap": "curiosity_gap", "curiosity": "curiosity_gap",
    "bold_claim": "bold_claim", "bold_honest_claim": "bold_claim",
    "bold": "bold_claim",
    "question": "question", "question_hook": "question",
    "number_detail": "number_detail", "number": "number_detail",
    "specific_detail": "number_detail",
    "number_specific_detail": "number_detail",
    "contrast": "contrast", "contrast_hook": "contrast",
}

_MAX_HOOK_WORDS = 12  # hard sanity cap; the critic scores length


def write_hook_candidates(concept, location="", fix_notes=None):
    """Multi-candidate mode: 5 hooks, one per named formula.

    Returns {"ok": True, "candidates": [{"hook":..., "formula":...},
    ...]} with at least 3 usable candidates, or an honest failure
    dict. No best is picked here — the hook critic batch-scores the
    candidates and the strongest scorer wins.

    fix_notes: optional critic/gate notes a regeneration round
    must steer by.
    """
    formula_block = "\n".join(
        f'- "{key}": {desc}' for key, desc in HOOK_FORMULAS)
    fix_block = ""
    if fix_notes:
        fix_block = ("A previous batch was REJECTED by the quality "
                     "gate. Steer every new hook by these notes:\n- "
                     + "\n- ".join(str(n) for n in fix_notes) + "\n")
    prompt = (
        f"Concept: {concept}\nLocation: {location}\n" + fix_block +
        "Write FIVE candidate hooks for this video — exactly ONE "
        "per formula below, each built ONLY on its own formula:\n"
        + formula_block + "\n"
        "Every hook: MAX 8 words, understandable with the sound "
        "OFF (it is also the on-screen text), honest — the video "
        "must truly deliver on it. The five hooks must be genuinely "
        "different lines, not rewordings of each other.\n"
        'Reply ONLY valid JSON: {"candidates": [{"formula": '
        '"curiosity_gap", "hook": "..."}, {"formula": "bold_claim", '
        '"hook": "..."}, {"formula": "question", "hook": "..."}, '
        '{"formula": "number_detail", "hook": "..."}, {"formula": '
        '"contrast", "hook": "..."}]}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=800, temperature=0.9)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    candidates, seen = [], set()
    for item in data.get("candidates", []) or []:
        if isinstance(item, dict):
            hook = str(item.get("hook", "")).strip()
            raw = str(item.get("formula", "")).strip().lower()
        else:
            hook, raw = str(item).strip(), ""
        key = _FORMULA_ALIASES.get(raw.replace(" ", "_").replace("-", "_"))
        if not hook or hook.lower() in seen:
            continue
        if len(hook.split()) > _MAX_HOOK_WORDS:
            continue
        seen.add(hook.lower())
        candidates.append({"hook": hook, "formula": key or "other"})
    if len(candidates) < 3:
        return fail("AI returned too few usable hook candidates")
    return {"ok": True, "ai_used": True, "candidates": candidates}


HOOK_MASTER_ROBOT = {"write_hooks": write_hooks,
                     "write_hook_candidates": write_hook_candidates,
                     "HOOK_FORMULAS": HOOK_FORMULAS}
