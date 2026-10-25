"""ULTIMATE ROBOT TEAM — content_factory/hashtag_researcher.py

Content Factory robot 10 of 20: the hashtag researcher.

Builds the hashtag set for a package: a layered mix — 2-3 broad
travel tags, 3-4 niche/location tags, 1-2 series/community tags,
plus #Shorts for YouTube. English only, each starting with #.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the hashtag researcher of a travel short-form channel. "
    "You pick hashtags real viewers actually search and browse — a "
    "mix of broad reach and tight niche. No spam tags, no unrelated "
    "tags, no invented event tags. Reply with ONLY valid JSON, no "
    "other text."
)


def research_hashtags(concept, location="", series_name=""):
    """Return {"ok": True, "hashtags": [7-10 tags]}."""
    prompt = (
        f"Concept: {concept}\nLocation: {location}\n"
        f"Series: {series_name}\n"
        "Give 7-10 English hashtags for this Short, layered:\n"
        "- 2-3 broad travel tags (e.g. #TravelCanada style reach)\n"
        "- 3-4 niche tags for the exact location / activity\n"
        "- 1-2 community or series tags\n"
        "- always include #Shorts\n"
        'Reply ONLY valid JSON: {"hashtags": ["#...", "..."]}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=400, temperature=0.6)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    tags = []
    for t in data.get("hashtags", []):
        t = str(t).strip()
        if not t:
            continue
        tags.append(t if t.startswith("#") else "#" + t)
    if "#Shorts" not in tags:
        tags.append("#Shorts")
    if len(tags) < 5:
        return fail("AI returned too few hashtags")
    return {"ok": True, "ai_used": True, "hashtags": tags[:10]}


HASHTAG_RESEARCHER_ROBOT = {"research_hashtags": research_hashtags}
