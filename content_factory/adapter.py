"""ULTIMATE ROBOT TEAM — content_factory/adapter.py

Content Factory robot 14 of 20: the adapter.

Rewrites ONE finished package into per-platform versions — the same
content, shaped for each surface:
- YouTube Shorts: hook-formula title + description with links.
- Instagram Reels: caption-first version (hashtags at the end).
- Facebook Reels: caption-first version for the Cyrus Outdoors page.
- WhatsApp channel: a short broadcast text with the video link line.
- Telegram: a short post for @Cyrus_team_bot with the links.
The primary platform for factory shorts is YouTube; the
orchestrator records it as the queue entry's platform.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import (  # noqa: E402
    APPROVED_FACTS, channels_block, fail, role_ask)

_SYSTEM = (
    "You are the platform adapter of the 'Cyrus AI' social team. "
    "You reshape one piece of content for each platform's habits "
    "without changing its facts. " + APPROVED_FACTS +
    " Reply with ONLY valid JSON, no other text."
)


def adapt_package(title, caption, hook, hashtags):
    """Return {"ok": True, "platforms": {...}, "primary_platform":
    "youtube"} or an honest failure dict."""
    tags = " ".join(hashtags or [])
    prompt = (
        f"Title: {title}\nHook: \"{hook}\"\nCaption:\n{caption}\n"
        f"Hashtags: {tags}\n" + channels_block() + "\n"
        "Adapt this package for 5 platforms:\n"
        "- youtube: {title (keep the given title unless a small "
        "tightening helps), description: 2-3 short sentences + the "
        "call to action + the YouTube and WhatsApp links + the "
        "hashtags}.\n"
        "- instagram: {caption: the caption rewritten for Reels — "
        "hook line first, hashtags grouped at the very end}.\n"
        "- facebook: {caption: the caption rewritten for Facebook "
        "Reels on the Cyrus Outdoors page — hook line first, "
        "hashtags grouped at the very end}.\n"
        "- whatsapp: {text: a SHORT channel broadcast (max ~60 "
        "words) with the hook, one line about the video, and the "
        "website link}.\n"
        "- telegram: {text: a short post for the Telegram channel "
        "with the hook, the website and YouTube links}.\n"
        'Reply ONLY valid JSON: {"youtube": {"title": "...", '
        '"description": "..."}, "instagram": {"caption": "..."}, '
        '"facebook": {"caption": "..."}, '
        '"whatsapp": {"text": "..."}, "telegram": {"text": "..."}}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=1100, temperature=0.6)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    yt = data.get("youtube") or {}
    desc = str(yt.get("description", "")).strip()
    if not desc:
        return fail("AI returned no YouTube adaptation")
    platforms = {
        "youtube": {
            "title": str(yt.get("title", "")).strip() or title,
            "description": desc,
        },
        "instagram": {"caption": str(
            (data.get("instagram") or {}).get("caption", "")).strip()},
        "facebook": {"caption": str(
            (data.get("facebook") or {}).get("caption", "")).strip()},
        "whatsapp": {"text": str(
            (data.get("whatsapp") or {}).get("text", "")).strip()},
        "telegram": {"text": str(
            (data.get("telegram") or {}).get("text", "")).strip()},
    }
    return {"ok": True, "ai_used": True, "platforms": platforms,
            "primary_platform": "youtube"}


ADAPTER_ROBOT = {"adapt_package": adapt_package}
