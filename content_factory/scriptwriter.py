"""ULTIMATE ROBOT TEAM — content_factory/scriptwriter.py

Content Factory robot 4 of 20: the scriptwriter.

Writes the host's spoken script for a 10-30 second short: the hook
line first (word-for-word the hook master's best hook), then 3-5
short spoken lines, ending with a soft Cyrus AI call to action and
a comment-bait question when it fits. Timed lines, easy words — the
host speaks like a friendly human, not an ad.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import (  # noqa: E402
    APPROVED_FACTS, HOST_BLOCK, fail, role_ask)

_SYSTEM = (
    "You are the scriptwriter for a travel short-form channel. You "
    "write short spoken scripts for ONE presenter: warm, simple "
    "words, natural rhythm, about 2.5 spoken words per second. "
    "HONEST always. " + APPROVED_FACTS +
    " Reply with ONLY valid JSON, no other text."
)


def write_script(concept, hook, location=""):
    """Return {"ok": True, "script": {spoken_text, lines, duration_sec}}.

    lines: [{"t": "0-2s", "text": "..."}] — the first line MUST be
    the hook, word for word.
    """
    prompt = (
        f"Concept: {concept}\nLocation: {location}\n"
        f"The hook (first line, word for word): \"{hook}\"\n"
        + HOST_BLOCK + "\n"
        "Write the host's full spoken script for a 10-30 second "
        "vertical video:\n"
        "- line 1 (0-2s) is the hook, EXACTLY as given.\n"
        "- then 3-5 short lines that deliver on the hook: one vivid "
        "detail, one useful honest tip, and the host's reaction.\n"
        "- last line: a soft call to action for Cyrus AI trip "
        "planning (only the approved facts) OR a question that "
        "invites comments.\n"
        "- total spoken words: 25-70.\n"
        'Reply ONLY valid JSON: {"spoken_text": "...", "lines": '
        '[{"t": "0-2s", "text": "..."}], "duration_sec": 20}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=800, temperature=0.75)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    spoken = str(data.get("spoken_text", "")).strip()
    lines = []
    for item in data.get("lines", []):
        if isinstance(item, dict) and str(item.get("text", "")).strip():
            lines.append({"t": str(item.get("t", "")).strip(),
                          "text": str(item["text"]).strip()})
    if not spoken and lines:
        spoken = " ".join(l["text"] for l in lines)
    if not spoken or not lines:
        return fail("AI returned an incomplete script")
    try:
        duration = int(data.get("duration_sec") or 0)
    except Exception:
        duration = 0
    if duration <= 0:
        duration = max(10, min(30, round(len(spoken.split()) / 2.5)))
    return {"ok": True, "ai_used": True, "script": {
        "spoken_text": spoken, "lines": lines,
        "duration_sec": duration}}


SCRIPTWRITER_ROBOT = {"write_script": write_script}
