"""ULTIMATE ROBOT TEAM — content_factory/cover_designer.py

Content Factory robot 11 of 20: the cover designer.

Writes the cover / first-frame brief: the cover text (max 4 words —
readable on a phone at a glance), WHICH frame of the storyboard to
freeze as the cover, and the layout (host position, text position,
contrast). The cover and the hook are one system: the first frame
must already sell the video.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the cover designer of a travel short-form channel. You "
    "know a cover is read in half a second on a small phone screen: "
    "few words, big emotion, the host's face visible. Reply with "
    "ONLY valid JSON, no other text."
)


def design_cover(concept, hook, storyboard=None):
    """Return {"ok": True, "cover": {cover_text, frame_choice,
    layout}} or an honest failure dict."""
    shots_text = ""
    if storyboard and storyboard.get("shots"):
        shots_text = "\nStoryboard shots:\n" + "\n".join(
            f"- [{s.get('t', '')}] {s.get('visual', '')}"
            for s in storyboard["shots"])
    prompt = (
        f"Concept: {concept}\nHook: \"{hook}\"\n" + shots_text + "\n"
        "Design the cover / first frame:\n"
        "- cover_text: MAX 4 words, huge and readable, creates the "
        "same curiosity as the hook without repeating it word for "
        "word.\n"
        "- frame_choice: which storyboard moment to freeze, and the "
        "host's expression in it.\n"
        "- layout: where the host stands, where the text sits, and "
        "the colour/contrast note.\n"
        'Reply ONLY valid JSON: {"cover_text": "...", '
        '"frame_choice": "...", "layout": "..."}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=500, temperature=0.7)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    text = str(data.get("cover_text", "")).strip()
    if not text:
        return fail("AI returned no cover text")
    return {"ok": True, "ai_used": True, "cover": {
        "cover_text": text,
        "frame_choice": str(data.get("frame_choice", "")).strip(),
        "layout": str(data.get("layout", "")).strip(),
    }}


COVER_DESIGNER_ROBOT = {"design_cover": design_cover}
