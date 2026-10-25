"""ULTIMATE ROBOT TEAM — content_factory/storyboarder.py

Content Factory robot 5 of 20: the storyboarder.

Breaks the script into a shot-by-shot storyboard the video can be
generated (or filmed) from: each shot has its time window, the
visual, the host's action, and the on-screen overlay text. The first
shot always carries the hook text — on screen from frame one.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import HOST_BLOCK, fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the storyboarder of a travel short-form team. You turn "
    "scripts into clear, producible shot lists for vertical video "
    "(9:16). Every shot must be generatable as AI video of the same "
    "host. Reply with ONLY valid JSON, no other text."
)


def make_storyboard(concept, script, hook):
    """Return {"ok": True, "storyboard": {"shots": [shot, ...]}}.

    script: the scriptwriter's script dict (spoken_text + lines).
    Each shot: {"t", "visual", "host_action", "overlay"}.
    """
    lines_text = "\n".join(
        f"[{l.get('t', '')}] {l.get('text', '')}"
        for l in script.get("lines", []))
    prompt = (
        f"Concept: {concept}\nHook: \"{hook}\"\n"
        f"Script lines:\n{lines_text}\n" + HOST_BLOCK + "\n"
        "Make a shot-by-shot storyboard (4-7 shots) covering the "
        "whole script. Rules:\n"
        "- shot 1 starts at 0s, shows the host facing camera, and "
        "its overlay is the HOOK text exactly.\n"
        "- every shot: t (e.g. \"0-2s\"), visual (what the camera "
        "sees, one sentence), host_action (what the host does), "
        "overlay (on-screen text for that shot, or an empty string).\n"
        "- keep the SAME host and location in every shot.\n"
        'Reply ONLY valid JSON: {"shots": [{"t": "0-2s", "visual": '
        '"...", "host_action": "...", "overlay": "..."}]}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=900, temperature=0.6)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    shots = []
    for item in data.get("shots", []):
        if not isinstance(item, dict):
            continue
        visual = str(item.get("visual", "")).strip()
        if not visual:
            continue
        shots.append({
            "t": str(item.get("t", "")).strip(),
            "visual": visual,
            "host_action": str(item.get("host_action", "")).strip(),
            "overlay": str(item.get("overlay", "")).strip(),
        })
    if len(shots) < 3:
        return fail("AI returned too few storyboard shots")
    return {"ok": True, "ai_used": True,
            "storyboard": {"shots": shots}}


STORYBOARDER_ROBOT = {"make_storyboard": make_storyboard}
