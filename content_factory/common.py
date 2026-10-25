"""ULTIMATE ROBOT TEAM — content_factory/common.py

Shared helpers for the 20-robot Content Factory: the AI host's fixed
identity, the approved-facts block every robot must respect, the
technique list, and a thin role-ask wrapper over brain/llm.py — the
same ask_json plumbing every smart robot on this team uses.

Honesty rules (team standard): no invented prices, hours, phone
numbers, or place facts. On AI failure the helpers return None and
each robot reports an honest failure — the factory never fakes
content. Keys come from the environment only, never printed.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.channels import channels_text  # noqa: E402
from brain.llm import ask_json  # noqa: E402

HOST_LABEL = "red-haired AI host"

HOST_BLOCK = (
    "THE HOST — identical in every piece of content: a woman in her "
    "early 30s with long, voluminous curly RED hair, a warm genuine "
    "smile, light freckles and natural makeup. She is the AI presenter "
    "of the Cyrus AI channel — an AI host for an AI travel-planning "
    "product. She is openly AI, never presented as a real human tour "
    "guide. Her wardrobe matches the location (rain jacket in Tofino, "
    "cozy sweater by Victoria's harbour, light dress at a lake...)."
)

APPROVED_FACTS = (
    "APPROVED FACTS — the ONLY product facts that may be stated: "
    "Cyrus AI trip planning costs CA$10 for 14 days at "
    "victoriatourandadventure.com; the app 'Cyrus AI Tour Guide' is "
    "on Google Play. NEVER invent prices, opening hours, phone "
    "numbers, distances, ferry times or facts about places — keep "
    "place talk general, visual and emotional."
)

TECHNIQUES = (
    "Proven short-form techniques available: (1) the HOOK — a "
    "scroll-stopping first 2 seconds; (2) curiosity gap — open a "
    "question the video then answers; (3) pattern interrupt — an "
    "unexpected first frame or first line; (4) series / ritual "
    "formats the viewer can follow every day; (5) a comment-bait "
    "question at the end; (6) trending formats and sounds when they "
    "fit honestly."
)


def fail(reason):
    return {"ok": False, "ai_used": False, "error": reason}


def lessons_block(lessons):
    """Format LearningBrain lessons for prompt injection (team style)."""
    if not lessons:
        return ""
    return ("Lessons learned from past feedback — you MUST apply "
            "them:\n- " + "\n- ".join(str(l) for l in lessons[:8]) + "\n")


def role_ask(system, prompt, max_tokens=800, temperature=0.7):
    """One AI call for one factory robot.

    Returns the parsed JSON dict, or None on any failure — the caller
    reports the failure honestly instead of faking content.
    """
    data, ai_used = ask_json(prompt, system, max_tokens=max_tokens,
                             temperature=temperature)
    if not ai_used or not isinstance(data, dict):
        return None
    return data


def channels_block():
    """The team's channel registry, formatted for prompts."""
    return ("Our channels — use the matching links for "
            "cross-promotion:\n" + channels_text())
