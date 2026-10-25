"""ULTIMATE ROBOT TEAM — content_factory/title_writer.py

Content Factory robot 8 of 20: the title writer.

Writes titles for YouTube Shorts / Reels built ON the hook: short,
searchable, and honest — the title promises exactly what the video
delivers. Returns 3 candidates and its best pick.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import APPROVED_FACTS, fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the title writer of a travel short-form channel. Your "
    "titles are built on the video's hook: max ~60 characters, the "
    "place name included when it helps search, catchy but HONEST — "
    "no clickbait the video cannot deliver. " + APPROVED_FACTS +
    " Reply with ONLY valid JSON, no other text."
)


def write_titles(concept, hook, location=""):
    """Return {"ok": True, "titles": [3], "best_title": ...}."""
    prompt = (
        f"Concept: {concept}\nHook: \"{hook}\"\nLocation: {location}\n"
        "Write 3 titles for this Short (max ~60 characters each): "
        "one built directly on the hook, one with the place name "
        "first (search-friendly), one as a question. Then name the "
        "single best one.\n"
        'Reply ONLY valid JSON: {"titles": ["...", "...", "..."], '
        '"best_title": "..."}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=450, temperature=0.8)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    titles = [str(t).strip() for t in data.get("titles", []) if str(t).strip()]
    best = str(data.get("best_title", "")).strip()
    if not titles or not best:
        return fail("AI returned incomplete titles")
    if best not in titles:
        titles.insert(0, best)
    return {"ok": True, "ai_used": True, "titles": titles[:3],
            "best_title": best}


TITLE_WRITER_ROBOT = {"write_titles": write_titles}
