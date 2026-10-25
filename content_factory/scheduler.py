"""ULTIMATE ROBOT TEAM — content_factory/scheduler.py

Content Factory robot 19 of 20: the scheduler.

LOCKED CADENCE (Cyrus's decision, 2026-10-25 — he delegated the
choice and it was locked): **1 strong content piece per day on
EVERY platform** — YouTube Shorts, Instagram Reels, the WhatsApp
channel and Telegram. Quality over volume: one piece that passed
the >= 8/10 gate, every day, no gaps. (Strategy: build a 2-week
content bank first, then publish daily without gaps.)

YouTube may rise to 2 pieces/day ONLY as a later phase — after
2-3 weeks of good watch metrics — and only by flipping the
`youtube_phase2` flag below to True. It is OFF by default and
nothing in this module turns it on automatically.

This robot suggests the posting SLOT (the time of day, from the AI
brain) — but the cadence itself is NOT the AI's choice: it is the
locked constant above, returned verbatim with every suggestion.
The suggestion is ADVICE stored in the queue entry — the human
still approves every post in approve.py, and the team's runner
decides the actual publish moment from the approval.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import fail, role_ask  # noqa: E402

# --- THE LOCKED CADENCE (2026-10-25) --------------------------------
PLATFORMS = ["youtube", "instagram", "facebook", "whatsapp", "telegram"]
DAILY_PER_PLATFORM = 1
# Phase 2 (YouTube 2/day) stays OFF until 2-3 weeks of good watch
# metrics say otherwise. Flip ONLY by a human decision.
youtube_phase2 = False
CADENCE_TEXT = (
    "1 strong content piece per day on every platform "
    "(YouTube Shorts, Instagram Reels, Facebook Reels, WhatsApp "
    "channel, Telegram)"
)


def daily_volume(phase2=None):
    """Pieces per day per platform under the locked cadence.

    phase2: None -> the module flag `youtube_phase2` (default
    False). True raises ONLY YouTube to 2/day.
    """
    if phase2 is None:
        phase2 = youtube_phase2
    volume = {p: DAILY_PER_PLATFORM for p in PLATFORMS}
    if phase2:
        volume["youtube"] = 2
    return volume


_SYSTEM = (
    "You are the posting scheduler of a travel short-form channel "
    "based in Victoria, BC (Pacific Time), whose audience plans "
    "Canada/USA trips from North America and Europe. The cadence is "
    "FIXED at one strong piece per day — you only choose the time "
    "of day. You suggest posting times in plain local terms — no "
    "invented statistics, just sound reasoning about when "
    "travellers scroll. Reply with ONLY valid JSON, no other text."
)


def suggest_slot(concept, platform="youtube"):
    """Return {"ok": True, "schedule": {slot, cadence, daily_volume,
    youtube_phase2, reason}} — cadence/volume come from the locked
    constants above, never from the AI."""
    prompt = (
        f"Concept: {concept}\nPrimary platform: {platform} (Shorts)\n"
        "The cadence is locked at 1 piece per day. Suggest only: "
        "slot (the best posting time of day for this kind of video, "
        "e.g. \"7:30 AM PT\") and reason (one honest sentence).\n"
        'Reply ONLY valid JSON: {"slot": "...", "reason": "..."}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=400, temperature=0.5)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    slot = str(data.get("slot", "")).strip()
    if not slot:
        return fail("AI returned no posting slot")
    return {"ok": True, "ai_used": True, "schedule": {
        "slot": slot,
        "cadence": CADENCE_TEXT,
        "daily_volume": daily_volume(),
        "youtube_phase2": youtube_phase2,
        "reason": str(data.get("reason", "")).strip(),
    }}


SCHEDULER_ROBOT = {"suggest_slot": suggest_slot,
                   "daily_volume": daily_volume,
                   "CADENCE_TEXT": CADENCE_TEXT}
