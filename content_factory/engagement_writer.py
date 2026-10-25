"""ULTIMATE ROBOT TEAM — content_factory/engagement_writer.py

Content Factory robot 15 of 20: the engagement writer.

Prepares the conversation kit that ships with every package: the
pinned comment (posted by the channel right after upload), the
comment-bait question the host asks, and 3 reply starters so
answering comments is fast and warm. Comments are where the
algorithm decides a video is alive — this robot feeds that.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import APPROVED_FACTS, fail, role_ask  # noqa: E402

_SYSTEM = (
    "You are the engagement writer of a travel short-form channel. "
    "You start real conversations in the comments: honest questions, "
    "warm replies, zero spam, zero fake promises. "
    + APPROVED_FACTS + " Reply with ONLY valid JSON, no other text."
)


def write_engagement(concept, hook, location=""):
    """Return {"ok": True, "engagement": {pinned_comment, question,
    reply_starters}} or an honest failure dict."""
    prompt = (
        f"Concept: {concept}\nHook: \"{hook}\"\nLocation: {location}\n"
        "Write the engagement kit for this Short:\n"
        "- pinned_comment: the channel's own first comment — adds "
        "one extra honest detail about the place and ends with the "
        "question.\n"
        "- question: ONE easy, fun question any viewer can answer "
        "in a few words (this is also the video's closing question).\n"
        "- reply_starters: 3 short warm replies the channel can use "
        "when viewers answer (vary them; one may point softly to "
        "Cyrus AI trip planning with only the approved facts).\n"
        'Reply ONLY valid JSON: {"pinned_comment": "...", '
        '"question": "...", "reply_starters": ["...", "...", "..."]}'
    )
    data = role_ask(_SYSTEM, prompt, max_tokens=600, temperature=0.8)
    if data is None:
        return fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    pinned = str(data.get("pinned_comment", "")).strip()
    question = str(data.get("question", "")).strip()
    starters = [str(s).strip() for s in data.get("reply_starters", [])
                if str(s).strip()]
    if not pinned or not question:
        return fail("AI returned an incomplete engagement kit")
    return {"ok": True, "ai_used": True, "engagement": {
        "pinned_comment": pinned, "question": question,
        "reply_starters": starters[:3]}}


ENGAGEMENT_WRITER_ROBOT = {"write_engagement": write_engagement}
