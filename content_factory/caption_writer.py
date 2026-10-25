"""ULTIMATE ROBOT TEAM — content_factory/caption_writer.py

Content Factory robot 9 of 20: the caption writer (factory edition —
the team's original caption robot lives in robots/content_robots.py;
this one writes the caption that travels WITH a finished factory
package).

Rules: the first line echoes the hook, 2-4 short paragraphs, one
soft Cyrus AI call to action using only the approved facts, and the
team's channel cross-promotion. Past lessons are injected so the
same mistakes are not repeated.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import (  # noqa: E402
    APPROVED_FACTS, channels_block, fail, lessons_block, role_ask)

_SYSTEM = (
    "You are the caption writer of the 'Cyrus AI' travel channel. "
    "Warm, short, human captions in English. " + APPROVED_FACTS +
    " Reply with ONLY valid JSON, no other text."
)


def write_caption(concept, hook, location="", lessons=None):
    """Return {"ok": True, "caption": "..."} or an honest failure."""
    prompt = (
        f"Concept: {concept}\nHook: \"{hook}\"\nLocation: {location}\n"
        "Write the post caption for this Short:\n"
        "- first line echoes the hook (it is what shows before "
        "\"...more\").\n"
        "- 2-4 short paragraphs: the moment, one honest useful "
        "detail, and a soft call to action for Cyrus AI trip "
        "planning using ONLY the approved facts.\n"
        "- end with the cross-promotion lines from our channels "
        "block (YouTube + WhatsApp + website or app — pick the 3 "
        "that fit a video post).\n"
        + lessons_block(lessons) + channels_block() + "\n"
        "Do NOT add hashtags (the hashtag researcher adds them).\n"
        'Reply ONLY valid JSON: {"caption": "..."}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=800, temperature=0.7)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    caption = str(data.get("caption", "")).strip()
    if not caption:
        return fail("AI returned an empty caption")
    return {"ok": True, "ai_used": True, "caption": caption}


CAPTION_WRITER_ROBOT = {"write_caption": write_caption}
