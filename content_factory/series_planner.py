"""ULTIMATE ROBOT TEAM — content_factory/series_planner.py

Content Factory robot 7 of 20: the series planner.

Fits each concept into a recurring SERIES format — the ritual that
turns one-off viewers into followers (e.g. "One Minute Victoria",
"Ask the AI Host", "Canada or USA?"). Every package leaves with a
series name, an episode label, the ritual element the viewer learns
to expect, and a tease for the next episode.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the series planner of a travel short-form channel. You "
    "design repeatable series formats with a recognisable ritual — "
    "the same opening energy, the same closing beat — so viewers "
    "come back daily. Reply with ONLY valid JSON, no other text."
)

_KNOWN_SERIES = (
    "Existing series on the channel (reuse one when the concept "
    "fits): \"One Minute Victoria\" (one Victoria spot per episode), "
    "\"Tofino Diaries\" (west-coast beach and surf moments), "
    "\"Ask the AI Host\" (the host answers one travel question), "
    "\"Canada or USA?\" (honest side-by-side travel choices), "
    "\"Plan With Me\" (the host builds a mini trip plan with "
    "Cyrus AI). Invent a new series ONLY when none of these fit."
)


def plan_series(concept, location=""):
    """Return {"ok": True, "series": {series_name, episode_label,
    ritual, next_tease}} or an honest failure dict."""
    prompt = (
        f"Concept: {concept}\nLocation: {location}\n"
        + _KNOWN_SERIES + "\n"
        "Assign this concept to a series and give: series_name, "
        "episode_label (e.g. \"Day 12\" or \"Episode 7\" style label "
        "WITHOUT a specific number — use \"next episode\"), ritual "
        "(the repeatable element viewers learn to expect, one "
        "sentence), next_tease (one line teasing the next episode, "
        "spoken or on-screen at the end).\n"
        'Reply ONLY valid JSON: {"series_name": "...", '
        '"episode_label": "...", "ritual": "...", "next_tease": "..."}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=500, temperature=0.7)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    name = str(data.get("series_name", "")).strip()
    if not name:
        return fail("AI returned no series name")
    return {"ok": True, "ai_used": True, "series": {
        "series_name": name,
        "episode_label": str(data.get("episode_label", "")).strip(),
        "ritual": str(data.get("ritual", "")).strip(),
        "next_tease": str(data.get("next_tease", "")).strip(),
    }}


SERIES_PLANNER_ROBOT = {"plan_series": plan_series}
