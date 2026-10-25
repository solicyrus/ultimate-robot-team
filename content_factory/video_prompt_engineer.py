"""ULTIMATE ROBOT TEAM — content_factory/video_prompt_engineer.py

Content Factory robot 6 of 20: the video prompt engineer.

Writes the ready-to-paste prompt for an AI video generator (Veo /
Kling / Runway style) so the produced clip keeps the SAME host in
every video: the host-consistency block from common.py is embedded
verbatim, plus the location, wardrobe, camera and mood for this
concept, and a negative prompt against the usual AI-video failures
(changing face, extra fingers, warped text...).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import HOST_BLOCK, fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the video prompt engineer of a travel short-form team. "
    "You write precise prompts for AI video generators. Your first "
    "law: CHARACTER CONSISTENCY — the same host, described the same "
    "way, in every video. Reply with ONLY valid JSON, no other text."
)

_NEGATIVE = (
    "different woman, changing face, changing hairstyle, blonde or "
    "dark hair, deformed hands, extra fingers, warped text, "
    "watermark, logo, blurry, low quality, cartoon, uncanny valley"
)


def make_video_prompt(concept, location="", setting="", storyboard=None):
    """Return {"ok": True, "video_prompt": {...}} with a paste-ready
    prompt, the fixed negative prompt, and format settings."""
    shots_text = ""
    if storyboard and storyboard.get("shots"):
        shots_text = "\nShots to cover:\n" + "\n".join(
            f"- [{s.get('t', '')}] {s.get('visual', '')}"
            for s in storyboard["shots"])
    prompt = (
        f"Concept: {concept}\nLocation: {location}\n"
        f"Setting: {setting}\n" + shots_text + "\n"
        "Write ONE ready-to-paste prompt for an AI video generator "
        "for this exactly-30-second vertical video. The action must "
        "fill the full 30 seconds, opening with the explosive hook "
        "shot in the first 2 seconds. The prompt MUST start "
        "with this host description, kept word-for-word consistent:\n"
        + HOST_BLOCK + "\n"
        "Then add: the exact location and setting, her wardrobe for "
        "this place, camera style (handheld phone look, natural "
        "light), her actions following the shots, and the mood. "
        "Photorealistic, vertical 9:16.\n"
        'Reply ONLY valid JSON: {"prompt_text": "...", "wardrobe": '
        '"...", "camera": "...", "mood": "..."}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=800, temperature=0.6)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    text = str(data.get("prompt_text", "")).strip()
    if not text:
        return fail("AI returned an empty video prompt")
    return {"ok": True, "ai_used": True, "video_prompt": {
        "prompt_text": text,
        "negative_prompt": _NEGATIVE,
        "wardrobe": str(data.get("wardrobe", "")).strip(),
        "camera": str(data.get("camera", "")).strip(),
        "mood": str(data.get("mood", "")).strip(),
        "aspect_ratio": "9:16",
        "host_consistency": HOST_BLOCK,
    }}


VIDEO_PROMPT_ENGINEER_ROBOT = {"make_video_prompt": make_video_prompt}
