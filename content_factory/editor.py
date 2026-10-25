"""ULTIMATE ROBOT TEAM — content_factory/editor.py

Content Factory robot 12 of 20: the editor.

Writes the assembly brief the video is finished with: the overlay
timeline (which text appears when), the hook-text timing (on screen
from 0.0s, held through the hook line), where the Cyrus AI logo
sits, the end card (what it shows, when it starts), and cut/music
sync notes. A package is not finished until this brief exists.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the editor of a travel short-form channel. You finish "
    "vertical videos: text overlays that appear exactly on the "
    "spoken words, a visible-but-tasteful brand logo, and a clean "
    "end card with the call to action. Reply with ONLY valid JSON, "
    "no other text."
)


def make_edit_brief(concept, hook, storyboard, series=None):
    """Return {"ok": True, "edit_brief": {...}} or an honest failure.

    storyboard: the storyboarder's dict. series: optional series
    dict (its next-episode tease belongs on the end card).
    """
    shots_text = "\n".join(
        f"- [{s.get('t', '')}] visual: {s.get('visual', '')} | "
        f"overlay: {s.get('overlay', '')}"
        for s in (storyboard or {}).get("shots", []))
    tease = (series or {}).get("next_tease", "")
    prompt = (
        f"Concept: {concept}\nHook: \"{hook}\"\n"
        f"Storyboard:\n{shots_text}\n"
        f"Series next-episode tease for the end card: \"{tease}\"\n"
        "Write the assembly brief:\n"
        "- overlay_timeline: one item per overlay {t, text, style} — "
        "the HOOK text enters at 0.0s in big bold text and stays "
        "until the hook line ends.\n"
        "- hook_text_timing: one sentence on the hook overlay timing.\n"
        "- logo: where the Cyrus AI logo/watermark sits and its size "
        "(visible, tasteful, never covering the host's face).\n"
        "- end_card: last 2-3 seconds — what it shows (logo, the "
        "Cyrus AI call to action with the website, and the series "
        "tease).\n"
        "- cuts: pacing notes (where the pattern-interrupt cut or "
        "zoom goes).\n"
        'Reply ONLY valid JSON: {"overlay_timeline": [{"t": "0.0s", '
        '"text": "...", "style": "..."}], "hook_text_timing": "...", '
        '"logo": "...", "end_card": "...", "cuts": "..."}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=900, temperature=0.55)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    timeline = []
    for item in data.get("overlay_timeline", []):
        if isinstance(item, dict) and str(item.get("text", "")).strip():
            timeline.append({
                "t": str(item.get("t", "")).strip(),
                "text": str(item["text"]).strip(),
                "style": str(item.get("style", "")).strip(),
            })
    end_card = str(data.get("end_card", "")).strip()
    if not timeline or not end_card:
        return fail("AI returned an incomplete edit brief")
    return {"ok": True, "ai_used": True, "edit_brief": {
        "overlay_timeline": timeline,
        "hook_text_timing": str(data.get("hook_text_timing", "")).strip(),
        "logo": str(data.get("logo", "")).strip(),
        "end_card": end_card,
        "cuts": str(data.get("cuts", "")).strip(),
    }}


EDITOR_ROBOT = {"make_edit_brief": make_edit_brief}
