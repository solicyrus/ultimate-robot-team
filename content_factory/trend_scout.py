"""ULTIMATE ROBOT TEAM — content_factory/trend_scout.py

Content Factory robot 1 of 20: the trend scout.

Finds trending travel / short-form angles for the Cyrus AI channel
using the AI brain's knowledge of current short-form patterns,
combined with the factory's proven technique list. (The team's live
web watcher is robots/trend_watcher.py; this scout specialises in
angles that fit the AI host and the hook-first format.)

Returns {"ok": True, "trends": [{"angle", "why_now", "format_fit"}]}
or an honest failure dict. Never fakes trends.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import TECHNIQUES, fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the trend scout for the 'Cyrus AI' travel channel (AI "
    "trip planner for Canada and the USA, focus on Vancouver Island, "
    "Victoria, Tofino and the Pacific Northwest). You spot short-form "
    "video angles that are riding current viewing habits. You are "
    "specific and honest — no invented statistics, no fake 'viral' "
    "claims. Reply with ONLY valid JSON, no other text."
)


def find_trends(niche="Vancouver Island and Pacific Northwest travel",
                count=3):
    """Return up to `count` trend angles for the given niche."""
    prompt = (
        f"Find {count} strong short-form video angles for this niche: "
        f"{niche}\n"
        "Each angle must suit an exactly-30-second vertical video presented "
        "by the channel's AI host, and must be buildable with the "
        "proven techniques below.\n" + TECHNIQUES + "\n"
        "For each angle give: angle (the content angle in one line), "
        "why_now (why viewers are watching this kind of video now, one "
        "honest sentence), format_fit (which technique it uses best).\n"
        'Reply ONLY valid JSON: {"trends": [{"angle": "...", '
        '"why_now": "...", "format_fit": "..."}]}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=700, temperature=0.8)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    trends = []
    for item in data.get("trends", []):
        if not isinstance(item, dict):
            continue
        angle = str(item.get("angle", "")).strip()
        if not angle:
            continue
        trends.append({
            "angle": angle,
            "why_now": str(item.get("why_now", "")).strip(),
            "format_fit": str(item.get("format_fit", "")).strip(),
        })
    if not trends:
        return fail("AI returned no usable trends")
    return {"ok": True, "ai_used": True, "trends": trends[:count]}


TREND_SCOUT_ROBOT = {"find_trends": find_trends}
