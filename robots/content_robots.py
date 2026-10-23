"""ULTIMATE ROBOT TEAM — robots/content_robots.py

Four REAL content robots. Each one calls the real AI brain (brain/llm.py)
to do its job — no template strings, no random "confidence" scores.

Every function returns:
    {"ok": True, "ai_used": True, ...real content...}   on success
    {"ok": False, "ai_used": False, "error": "..."}     when the AI is
                                                        unavailable.

Failures are reported honestly — a robot never fakes content.
"""

from brain.llm import ask_json

_SYSTEM = (
    "You are an expert social-media content creator writing for a travel "
    "brand. You write in BOTH Persian and English. You NEVER invent prices, "
    "phone numbers, addresses, or facts you were not given. Reply with ONLY "
    "valid JSON, no other text."
)


def _fail(reason):
    return {"ok": False, "ai_used": False, "error": reason}


def caption_writer(topic, lessons=None):
    """Write one engaging Instagram/Telegram caption (Persian + English).

    lessons: optional list of lesson strings from LearningBrain — they are
    injected into the prompt so past mistakes are not repeated.

    Returns {"ok": True, "caption_fa": ..., "caption_en": ...}.
    """
    lesson_block = ""
    if lessons:
        lesson_block = (
            "Lessons learned from past feedback — you MUST apply them:\n- "
            + "\n- ".join(str(l) for l in lessons[:8]) + "\n")
    prompt = (
        f"Write one engaging social-media caption about: {topic}\n"
        "Rules: strong hook in the first line, 2-4 short paragraphs, "
        "one call-to-action, no invented prices or phone numbers.\n"
        + lesson_block +
        'Reply ONLY valid JSON: {"caption_fa": "...", "caption_en": "..."}'
    )
    data, ai_used = ask_json(prompt, _SYSTEM, max_tokens=700)
    if not ai_used or not data:
        return _fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    fa, en = data.get("caption_fa", ""), data.get("caption_en", "")
    if not fa or not en:
        return _fail("AI returned an incomplete caption")
    return {"ok": True, "ai_used": True, "topic": topic,
            "caption_fa": fa.strip(), "caption_en": en.strip()}


def title_maker(topic):
    """Write 5 viral-but-honest titles/hooks about the topic.

    Returns {"ok": True, "titles": [5 strings]}.
    """
    prompt = (
        f"Write 5 viral social-media titles (hooks) about: {topic}\n"
        "Mix Persian and English if natural. Catchy but HONEST — "
        "no clickbait lies, no invented facts.\n"
        'Reply ONLY valid JSON: {"titles": ["...", "...", "...", "...", "..."]}'
    )
    data, ai_used = ask_json(prompt, _SYSTEM, max_tokens=500)
    if not ai_used or not data:
        return _fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    titles = [t.strip() for t in data.get("titles", []) if str(t).strip()]
    if len(titles) < 3:
        return _fail("AI returned too few titles")
    return {"ok": True, "ai_used": True, "topic": topic,
            "titles": titles[:5]}


def hashtag_maker(topic):
    """Generate 15 effective hashtags (Persian + English mix).

    Returns {"ok": True, "hashtags": [15 strings]}.
    """
    prompt = (
        f"Generate 15 effective hashtags for social-media posts about: {topic}\n"
        "Mix Persian and English hashtags. Each must start with #.\n"
        'Reply ONLY valid JSON: {"hashtags": ["#...", ...15 items...]}'
    )
    data, ai_used = ask_json(prompt, _SYSTEM, max_tokens=500)
    if not ai_used or not data:
        return _fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    tags = [str(t).strip() for t in data.get("hashtags", []) if str(t).strip()]
    tags = [t if t.startswith("#") else "#" + t for t in tags]
    if len(tags) < 8:
        return _fail("AI returned too few hashtags")
    return {"ok": True, "ai_used": True, "topic": topic,
            "hashtags": tags[:15]}


def content_planner(niche):
    """Build a 7-day content calendar for the niche.

    Returns {"ok": True, "calendar": [{day, format, idea} x7]}.
    """
    prompt = (
        f"Create a 7-day social-media content calendar for this niche: {niche}\n"
        "One post idea per day. Vary the format: reel, carousel, story, photo post.\n"
        "Each idea: one clear sentence, honest, no invented facts.\n"
        'Reply ONLY valid JSON: {"calendar": ['
        '{"day": 1, "format": "reel", "idea": "..."}, '
        "...7 items total...]}"
    )
    data, ai_used = ask_json(prompt, _SYSTEM, max_tokens=900)
    if not ai_used or not data:
        return _fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    cal = data.get("calendar", [])
    if not isinstance(cal, list) or len(cal) < 5:
        return _fail("AI returned an incomplete calendar")
    return {"ok": True, "ai_used": True, "niche": niche,
            "calendar": cal[:7]}


# The four content robots, as a named team (each does real work).
CONTENT_ROBOTS = {
    "caption_writer": caption_writer,
    "title_maker": title_maker,
    "hashtag_maker": hashtag_maker,
    "content_planner": content_planner,
}
