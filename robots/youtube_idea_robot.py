"""ULTIMATE ROBOT TEAM — robots/youtube_idea_robot.py

Robot 13: the YouTube idea robot for the "Cyrus AI" channel (the team's
YouTube home — the repurposed Victoria Tour and Adventure channel).

What it does:
    Generates exactly 3 YouTube Shorts ideas per run with the real AI
    brain (brain/llm.py — the same ask_json plumbing every smart robot
    on this team uses). Every idea is built HOOK-FIRST (the "قلاب"
    technique): a scroll-stopping hook line for the first 2 seconds
    (max ~8 words, spoken + on-screen) plus WHY it hooks, then the full
    Short concept, a hook-formula title, a description, hashtags, and a
    call to action pointing to Cyrus AI.

    The 3 ideas are appended to approval_queue.json (via the shared
    ApprovalQueue in robots/runner.py — the same schema as every other
    queued post) with platform "youtube" and status awaiting_approval.

IRON RULE: this robot only PREPARES and queues. It never publishes,
never sends anything anywhere. A human approves in approve.py first.

Honesty rules (team standard): no invented prices, hours, phone
numbers, or facts. The only product facts used are the ones given in
the prompt below. Concepts must be filmable by the creator himself —
his own phone footage (Victoria / Vancouver Island) or a screen
recording of the Cyrus AI planner. On AI failure the robot reports an
honest error and queues NOTHING — it never fakes ideas.

Run (from the project root):
    python -m robots.youtube_idea_robot
    python -m robots.youtube_idea_robot "Banff in winter"
Needs: OPENAI_API_KEY in the environment (same as every AI robot).
"""

import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.channels import channels_text
from brain.learning import LearningBrain
from brain.llm import ask_json
from robots.runner import AWAITING, ApprovalQueue

_SYSTEM = (
    "You are the YouTube Shorts strategist for the 'Cyrus AI' channel — "
    "an AI tour guide / trip planner for Canada and the USA (focus: "
    "USA). Your craft is the HOOK: every Short opens with a "
    "scroll-stopping hook in the first 2 seconds. You are catchy but "
    "HONEST — no clickbait lies, no invented prices, hours, phone "
    "numbers, or facts. The only product facts you may use: Cyrus AI "
    "trip planning costs CA$10 for 14 days at "
    "victoriatourandadventure.com, and the app 'Cyrus AI Tour Guide' is "
    "on Google Play. Reply with ONLY valid JSON, no other text."
)

_IDEA_SHAPE = (
    '{"hook": "...", "hook_why": "...", "concept": "...", '
    '"title": "...", "description": "...", '
    '"hashtags": ["#...", ...], "cta": "..."}'
)


def _fail(reason):
    return {"ok": False, "ai_used": False, "error": reason}


def generate_ideas(focus=None, lessons=None):
    """Create exactly 3 hook-first YouTube Shorts ideas via the AI brain.

    focus:   optional topic steer (e.g. "Niagara Falls").
    lessons: optional list of lesson strings from LearningBrain — they
             are injected so past mistakes are not repeated.

    Returns {"ok": True, "ai_used": True, "ideas": [3 idea dicts]}
    or an honest _fail(...) dict when the AI is unavailable or its
    answer is incomplete. Nothing is queued here.
    """
    lesson_block = ""
    if lessons:
        lesson_block = (
            "Lessons learned from past feedback — you MUST apply them:\n- "
            + "\n- ".join(str(l) for l in lessons[:8]) + "\n")
    focus_line = (f"Steer all 3 ideas toward this focus: {focus}\n"
                  if focus else
                  "Spread the 3 ideas across the channel's niches: a "
                  "hidden gem, a wildlife/viewpoint moment, and a "
                  "Cyrus AI trip-planner demo or Canada-vs-USA travel "
                  "tip.\n")
    prompt = (
        "Create exactly 3 YouTube Shorts ideas for the Cyrus AI "
        "channel.\n"
        + focus_line +
        "EVERY idea must be HOOK-FIRST:\n"
        "- hook: the exact line spoken AND shown on screen in the "
        "first 2 seconds. MAX 8 words. It must stop the scroll — "
        "curiosity, surprise, or a bold honest claim the Short then "
        "delivers on.\n"
        "- hook_why: one sentence — why this hook stops the scroll.\n"
        "- concept: what the viewer sees, shot by shot in 2-4 short "
        "sentences. MUST be filmable by the creator himself: his own "
        "phone footage around Victoria / Vancouver Island, or a "
        "screen recording of the Cyrus AI planner building a trip "
        "plan. No stock footage, no places he cannot film.\n"
        "- title: a YouTube Shorts title built on the hook (max ~60 "
        "characters).\n"
        "- description: 2-3 short sentences ending with the "
        "call to action.\n"
        "- hashtags: 5-8 English hashtags, each starting with # "
        "(include #Shorts).\n"
        "- cta: one short call to action pointing to Cyrus AI "
        "(the CA$10 / 14-day planner at victoriatourandadventure.com "
        "or the Cyrus AI Tour Guide app).\n"
        + lesson_block +
        "Our channels — use the matching links in each description "
        "for cross-promotion (every YouTube description must also "
        "invite viewers to follow the WhatsApp channel):\n"
        + channels_text() + "\n"
        'Reply ONLY valid JSON: {"ideas": [' + _IDEA_SHAPE + ", "
        + _IDEA_SHAPE + ", " + _IDEA_SHAPE + "]}"
    )
    data, ai_used = ask_json(prompt, _SYSTEM, max_tokens=1600,
                             temperature=0.8)
    if not ai_used or not data:
        return _fail("AI unavailable (OPENAI_API_KEY missing or API error)")
    raw = data.get("ideas")
    if not isinstance(raw, list):
        return _fail("AI returned no ideas list")
    ideas = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        hook = str(item.get("hook", "")).strip()
        title = str(item.get("title", "")).strip()
        concept = str(item.get("concept", "")).strip()
        if not hook or not title or not concept:
            continue
        tags = [str(t).strip() for t in item.get("hashtags", [])
                if str(t).strip()]
        tags = [t if t.startswith("#") else "#" + t for t in tags]
        ideas.append({
            "hook": hook,
            "hook_why": str(item.get("hook_why", "")).strip(),
            "concept": concept,
            "title": title,
            "description": str(item.get("description", "")).strip(),
            "hashtags": tags[:8],
            "cta": str(item.get("cta", "")).strip(),
        })
    if len(ideas) < 3:
        return _fail(f"AI returned only {len(ideas)} complete idea(s), "
                     "need exactly 3 — nothing was queued")
    return {"ok": True, "ai_used": True, "ideas": ideas[:3]}


def _caption_for(idea):
    """The human-readable preview stored in the queue entry's caption
    field — this is what approve.py list shows the human."""
    return (
        f"🎬 YouTube Short idea — {idea['title']}\n"
        f"🪝 Hook (first 2 seconds): \"{idea['hook']}\"\n"
        f"Why it hooks: {idea['hook_why']}\n"
        f"Concept: {idea['concept']}\n"
        f"CTA: {idea['cta']}"
    )


def queue_ideas(ideas, queue=None):
    """Append the ideas to approval_queue.json in the team's schema.
    Returns the list of new entry ids. Queues ONLY — never publishes."""
    q = queue or ApprovalQueue()
    now = datetime.now().isoformat()
    ids = []
    for idea in ideas:
        pid = uuid.uuid4().hex[:8]
        entry = {
            "id": pid,
            "source_id": None,
            "caption": _caption_for(idea),
            "image_path": None,
            "image_note": ("no image — a YouTube Short is filmed by "
                           "the creator from his own footage"),
            "image_public_url": None,
            "scheduled_for": now,
            "created_at": now,
            "status": AWAITING,
            "channels": ["youtube"],
            "results": {},
            # YouTube idea payload (platform marker + full concept)
            "platform": "youtube",
            "format": "short",
            "title": idea["title"],
            "hook": idea["hook"],
            "hook_why": idea["hook_why"],
            "concept": idea["concept"],
            "description": idea["description"],
            "hashtags": idea["hashtags"],
            "cta": idea["cta"],
        }
        q.add(entry)
        ids.append(pid)
    return ids


def _print_summary_fa(ideas, ids):
    """Short Persian summary for the human (stdout)."""
    print("🎬 ربات ایده‌ی یوتیوب — ۳ ایده‌ی شورت جدید برای کانال Cyrus AI")
    print("هر ایده با تکنیک قلاب ساخته شده: اول ۲ ثانیه، یک جمله که اسکرول را نگه می‌دارد.\n")
    for i, (idea, pid) in enumerate(zip(ideas, ids), 1):
        print(f"{i}. {idea['title']}")
        print(f"   🪝 قلاب: «{idea['hook']}»")
        if idea["hook_why"]:
            print(f"   چرا می‌گیرد: {idea['hook_why']}")
        print(f"   شناسه در صف تأیید: {pid}")
    print("\nهر ۳ ایده در صف تأیید (approval_queue.json) با وضعیت "
          "«در انتظار تأیید» ثبت شدند. هیچ‌چیز منتشر نشده است — "
          "اول تأیید شما، بعد انتشار.")


def main(argv):
    focus = " ".join(argv[1:]).strip() or None
    try:
        lessons = LearningBrain().get_lessons()
    except Exception:
        lessons = None
    result = generate_ideas(focus=focus, lessons=lessons)
    if not result.get("ok"):
        print(f"ربات ایده‌ی یوتیوب ناموفق بود: {result.get('error')}",
              file=sys.stderr)
        print("هیچ ایده‌ای ساخته یا در صف ثبت نشد.", file=sys.stderr)
        return 1
    ids = queue_ideas(result["ideas"])
    _print_summary_fa(result["ideas"], ids)
    return 0


# The robot, as a named team member (each does real work).
YOUTUBE_IDEA_ROBOT = {
    "generate_ideas": generate_ideas,
    "queue_ideas": queue_ideas,
}


if __name__ == "__main__":
    sys.exit(main(sys.argv))
