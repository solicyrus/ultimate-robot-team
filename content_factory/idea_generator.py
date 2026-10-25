"""ULTIMATE ROBOT TEAM — content_factory/idea_generator.py

Content Factory robot 2 of 20: the idea generator.

Turns a trend angle (or a focus topic) into ONE concrete short-video
concept starring the channel's AI host. Concepts must be producible
as AI-generated video of the host (see video_prompt_engineer) or as
simple footage of the named place — and must avoid concepts already
in the librarian's ledger.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import (  # noqa: E402
    APPROVED_FACTS, HOST_BLOCK, TECHNIQUES, fail, lessons_block, role_ask)

_SYSTEM = (
    "You are the idea generator of a travel short-form content "
    "factory. You invent concrete, filmable video concepts starring "
    "one presenter. You are catchy but HONEST. " + APPROVED_FACTS +
    " Reply with ONLY valid JSON, no other text."
)


def generate_idea(focus=None, trend=None, lessons=None, avoid=None):
    """Create ONE concept.

    focus: optional topic steer (e.g. "Tofino in the rain").
    trend: optional trend dict from trend_scout.
    avoid: optional list of past concept summaries that must NOT be
           repeated (from the librarian's ledger).
    Returns {"ok": True, "idea": {concept, location, setting,
    host_moment, technique}} or an honest failure dict.
    """
    steer = ""
    if focus:
        steer += f"Focus topic: {focus}\n"
    if trend:
        steer += (f"Trend angle to ride: {trend.get('angle', '')} "
                  f"({trend.get('format_fit', '')})\n")
    if not steer:
        steer = ("Pick a fresh angle around Victoria / Vancouver "
                 "Island travel.\n")
    avoid_block = ""
    if avoid:
        avoid_block = ("Do NOT repeat or closely copy any of these "
                       "past concepts:\n- "
                       + "\n- ".join(str(a)[:120] for a in avoid[-12:])
                       + "\n")
    prompt = (
        "Create ONE short-video concept (10-30 seconds, vertical) for "
        "the Cyrus AI channel.\n" + steer + HOST_BLOCK + "\n"
        "The concept must star the host: she appears on camera at the "
        "location, speaks to the viewer, and the video ends by "
        "pointing to Cyrus AI trip planning.\n" + TECHNIQUES + "\n"
        + avoid_block + lessons_block(lessons) +
        "Give: concept (2-3 sentences: what happens, start to end), "
        "location (the real place), setting (time of day / weather / "
        "mood), host_moment (the host's key on-camera moment), "
        "technique (the main short-form technique used).\n"
        'Reply ONLY valid JSON: {"concept": "...", "location": "...", '
        '"setting": "...", "host_moment": "...", "technique": "..."}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=700, temperature=0.85)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    concept = str(data.get("concept", "")).strip()
    location = str(data.get("location", "")).strip()
    if not concept or not location:
        return fail("AI returned an incomplete concept")
    return {"ok": True, "ai_used": True, "idea": {
        "concept": concept,
        "location": location,
        "setting": str(data.get("setting", "")).strip(),
        "host_moment": str(data.get("host_moment", "")).strip(),
        "technique": str(data.get("technique", "")).strip(),
    }}


IDEA_GENERATOR_ROBOT = {"generate_idea": generate_idea}
