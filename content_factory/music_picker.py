"""ULTIMATE ROBOT TEAM — content_factory/music_picker.py

Content Factory robot 13 of 20: the music picker.

Writes the music/sound brief for a package: the mood, the tempo, the
kind of sound to pick in the platform's own library (described, not
invented — track names are chosen at upload time from the actual
trending audio in the app), and how the music ducks under the
host's voice.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the music picker of a travel short-form channel. You "
    "match sound to scene: the music carries the emotion, the "
    "host's voice always stays on top. You DESCRIBE the sound to "
    "pick from the platform's trending-audio library — you never "
    "invent fake track names or artists. Reply with ONLY valid "
    "JSON, no other text."
)


def pick_music(concept, setting=""):
    """Return {"ok": True, "music": {mood, tempo, sound_suggestion,
    voice_note}} or an honest failure dict."""
    prompt = (
        f"Concept: {concept}\nSetting: {setting}\n"
        "Write the music brief for this 30-second Short:\n"
        "- mood: the feeling the music must carry (2-4 words).\n"
        "- tempo: slow / mid / upbeat + where the energy rises.\n"
        "- sound_suggestion: describe the trending sound to search "
        "for in the platform library (style, instruments, vibe) — "
        "no invented track names.\n"
        "- voice_note: how the music sits under the host's spoken "
        "lines and when it may come forward.\n"
        'Reply ONLY valid JSON: {"mood": "...", "tempo": "...", '
        '"sound_suggestion": "...", "voice_note": "..."}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=450, temperature=0.6)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    mood = str(data.get("mood", "")).strip()
    if not mood:
        return fail("AI returned no music mood")
    return {"ok": True, "ai_used": True, "music": {
        "mood": mood,
        "tempo": str(data.get("tempo", "")).strip(),
        "sound_suggestion": str(data.get("sound_suggestion", "")).strip(),
        "voice_note": str(data.get("voice_note", "")).strip(),
    }}


MUSIC_PICKER_ROBOT = {"pick_music": pick_music}
