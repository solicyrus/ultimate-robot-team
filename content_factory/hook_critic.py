"""ULTIMATE ROBOT TEAM — content_factory/hook_critic.py

Content Factory robot 16 of 20: the hook critic.

Scores hooks 0-10 for scroll-stopping strength, with reasons and
a concrete fix. This is a JUDGE, not a writer: it is deliberately
strict — most hooks are a 5-7; an 8+ must genuinely earn it
(specific, surprising or curiosity-loaded, understandable muted,
and honest against what the video delivers).

Two judging modes:
- score_hook: ONE hook — the score that feeds the quality
  gatekeeper.
- score_hooks_batch: ALL of the hook master's formula candidates
  in one sitting, returned ranked — judging them side by side is
  sharper than judging one in isolation, and the orchestrator
  runs with the best scorer.
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


def _norm(s):
    return " ".join(str(s or "").lower().split()).strip("\"' ")


def score_hooks_batch(candidates, concept):
    """Batch-score the hook master's formula candidates.

    candidates: [{"hook":..., "formula":...}, ...] (plain strings
    also accepted). Returns {"ok": True, "ranked": [{hook, formula,
    score, reason}, ...] best first, "best_hook":..., "best_score":
    ...} or an honest failure dict when too few candidates come
    back scored to trust a winner.
    """
    cands = []
    for c in candidates or []:
        if isinstance(c, dict):
            hook = str(c.get("hook", "")).strip()
            formula = str(c.get("formula", "")).strip() or "other"
        else:
            hook, formula = str(c).strip(), "other"
        if hook:
            cands.append({"hook": hook, "formula": formula})
    if len(cands) < 2:
        return fail("too few hook candidates to batch-score")
    listing = "\n".join(
        f'{i}. [{c["formula"]}] "{c["hook"]}"'
        for i, c in enumerate(cands, 1))
    prompt = (
        f"The video they all open: {concept}\n"
        "Score EACH of these candidate hooks 0-10 on "
        "scroll-stopping strength, judging them against EACH "
        "OTHER as well as on their own. Same strictness as "
        "always:\n"
        "- curiosity: does it open a question the viewer must "
        "close?\n"
        "- specificity: concrete words beat vague ones.\n"
        "- muted test: does it work as on-screen text?\n"
        "- honesty: can THIS video truly deliver on it?\n"
        "- length: 8 words or fewer is full marks; longer loses.\n"
        "Be strict: 5-7 is a normal working hook. 8+ is rare and "
        "must be truly sharp. 9-10 is exceptional.\n"
        f"Candidates:\n{listing}\n"
        "Reply with one score per candidate, echoing each hook "
        "word for word, plus ONE short reason per hook.\n"
        'Reply ONLY valid JSON: {"scores": [{"hook": "...", '
        '"score": 7.5, "reason": "..."}]}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=800, temperature=0.35)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    scored = {}
    for item in data.get("scores", []) or []:
        if not isinstance(item, dict):
            continue
        try:
            value = float(item.get("score"))
        except (TypeError, ValueError):
            continue
        scored[_norm(item.get("hook", ""))] = (
            max(0.0, min(10.0, value)),
            str(item.get("reason", "")).strip())
    ranked = []
    for c in cands:
        hit = scored.get(_norm(c["hook"]))
        if hit is None:
            continue
        ranked.append({"hook": c["hook"], "formula": c["formula"],
                       "score": hit[0], "reason": hit[1]})
    if len(ranked) < 2:
        return fail("AI scored too few candidates to pick a winner")
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return {"ok": True, "ai_used": True, "ranked": ranked,
            "best_hook": ranked[0]["hook"],
            "best_score": ranked[0]["score"]}


HOOK_CRITIC_ROBOT = {"score_hook": score_hook,
                     "score_hooks_batch": score_hooks_batch}
