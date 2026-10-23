"""ULTIMATE ROBOT TEAM — main.py

The SuperRobot: a REAL orchestrator for 12 REAL robots.

The 12 robots:
    1. deep_think      (brain)      — real AI strategy via brain/llm.py
    2. memory_keeper   (brain)      — real JSON-persisted memory
    3. trend_watcher   (robots)     — real live-web DuckDuckGo search
    4. title_maker     (robots)     — real AI viral titles
    5. caption_writer  (robots)     — real AI Persian+English captions
                                       (past lessons injected)
    6. hashtag_maker   (robots)     — real AI hashtags
    7. scheduler       (robots)     — real JSON post queue
    8. telegram_publisher (robots)  — real Telegram Bot API (needs token)
    9. learning_brain  (brain)      — feedback-loop learning: feedback
                                       becomes durable lessons
                                       (brain/learning.py)
   10. auto_critic     (brain)      — strict editor reviews every draft
                                       against 5 standards, one revision
                                       loop (brain/critic.py)
   11. image_maker     (robots)     — real AI visual: Gemini writes the
                                       prompt, Imagen 3 renders a 1:1 PNG
                                       (needs GEMINI_API_KEY)
   12. instagram_publisher (robots) — real Meta Graph API two-step photo
                                       publish (needs IG_ACCESS_TOKEN +
                                       IG_USER_ID + a PUBLIC image URL)

A mission runs: think -> remember -> watch trends -> create content
(in parallel, lessons injected) -> critic reviews -> revise once if
needed -> queue the final post -> try Telegram (clean skip without
token) -> make the AI image (clean skip without key) -> try Instagram
(clean skip without token or public image URL) -> record the outcome
for future learning.

Run:  python main.py
Needs: OPENAI_API_KEY in the environment for the AI robots.
       GEMINI_API_KEY is optional (learning prefers Gemini, falls back
       to OpenAI; image_maker needs it too). Telegram publishing is
       OPTIONAL — without TELEGRAM_BOT_TOKEN the post stays queued and
       the run reports an honest skip. Instagram publishing is OPTIONAL
       — without IG_ACCESS_TOKEN/IG_USER_ID/IMAGE_PUBLIC_URL it is
       skipped honestly. With NO keys at all the run still completes:
       critic and learning use honest fallbacks instead of crashing.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain.critic import AutoCritic
from brain.learning import LearningBrain
from brain.llm import ask_json
from brain.memory import BrainMemory
from robots import content_robots
from robots import image_maker
from robots import instagram_publisher
from robots.scheduler import PostScheduler
from robots.telegram_publisher import publish as telegram_publish
from robots.trend_watcher import watch as watch_trends

VERSION = "real-v1.2"


class SuperRobot:
    """Real team orchestrator. Every step does real work or reports
    an honest failure — nothing is simulated."""

    def __init__(self):
        self.name = "SuperRobot"
        self.version = VERSION
        self.memory = BrainMemory()      # robot 2: memory_keeper
        self.scheduler = PostScheduler()  # robot 7: scheduler
        self.learning = LearningBrain()  # robot 9: learning_brain
        self.critic = AutoCritic()       # robot 10: auto_critic

    # -- robot 1: deep_think (the brain) ---------------------------------
    def deep_think(self, mission):
        """Real strategy thinking via the AI brain. Returns a real plan
        dict, or an honest failure when the AI is unavailable."""
        system = (
            "You are the strategy brain of a social-media robot team. "
            "Analyze the mission and produce a short step-by-step plan "
            "IN PERSIAN. Reply with ONLY valid JSON, no other text: "
            '{"reasoning": "...", "plan": ["step1", "step2", ...], '
            '"confidence": 0.0-1.0}'
        )
        data, ai_used = ask_json(mission, system, max_tokens=600)
        if not ai_used or not data:
            return {"ok": False, "ai_used": False,
                    "error": "AI brain unavailable "
                             "(OPENAI_API_KEY missing or API error)"}
        return {"ok": True, "ai_used": True,
                "reasoning": str(data.get("reasoning", "")),
                "plan": data.get("plan", []),
                "confidence": data.get("confidence")}

    # -- the mission ------------------------------------------------------
    async def run_mission(self, mission, niche):
        """Run one full mission end-to-end. Returns a real results dict."""
        out = {"mission": mission, "niche": niche,
               "super_robot": self.version, "steps": {}}

        # 1. brain thinks (real AI)
        thought = await asyncio.to_thread(self.deep_think, mission)
        out["steps"]["deep_think"] = thought

        # 2. memory_keeper persists the mission (real file write)
        self.memory.remember(
            "last_mission",
            {"mission": mission, "niche": niche,
             "thinking_ok": thought.get("ok")},
            important=True,
        )
        out["steps"]["memory_keeper"] = {"ok": True, "saved": True}

        # 3. trend_watcher searches the live web (real HTTP)
        trends = await asyncio.to_thread(watch_trends, niche)
        out["steps"]["trend_watcher"] = trends

        # 4. content team works in parallel (real AI calls).
        #    Lessons learned from past feedback are injected into the
        #    caption prompt so old mistakes are not repeated.
        lessons = self.learning.get_lessons()
        topic = niche
        if trends.get("ok") and trends.get("trends"):
            topic = f"{niche} — trending now: {trends['trends'][0]['title']}"
        titles, caption, tags = await asyncio.gather(
            asyncio.to_thread(content_robots.title_maker, topic),
            asyncio.to_thread(content_robots.caption_writer, topic,
                              lessons),
            asyncio.to_thread(content_robots.hashtag_maker, topic),
        )
        out["steps"]["title_maker"] = titles
        out["steps"]["caption_writer"] = caption
        out["steps"]["hashtag_maker"] = tags
        out["steps"]["learning_lessons_used"] = len(lessons)

        # 5. auto_critic reviews the draft (real AI judge, or an honest
        #    rule-based fallback with no key). One revision loop if the
        #    draft fails and the AI writer is available.
        critic_result = {"ok": False, "skipped": True,
                         "reason": "no content produced to review"}
        revised = False
        post_text = ""
        if caption.get("ok"):
            def build_post(cap):
                text = cap["caption_fa"] + "\n\n" + cap["caption_en"]
                if tags.get("ok"):
                    text += "\n\n" + " ".join(tags["hashtags"][:10])
                return text

            post_text = build_post(caption)
            critic_result = await asyncio.to_thread(
                self.critic.review, post_text)
            if (critic_result.get("ok")
                    and not critic_result.get("passed")
                    and critic_result.get("ai_used")):
                fix_topic = (topic + "\n\nREVISION REQUIRED — the editor "
                             "rejected the draft below. Rewrite it, fixing "
                             "every issue while keeping what was good:\n\n"
                             "DRAFT:\n" + post_text +
                             "\n\nEDITOR'S FIX LIST: "
                             + critic_result.get("suggestion", ""))
                caption2 = await asyncio.to_thread(
                    content_robots.caption_writer, fix_topic, lessons)
                if caption2.get("ok"):
                    caption = caption2
                    revised = True
                    post_text = build_post(caption)
                    critic_result = await asyncio.to_thread(
                        self.critic.review, post_text)
            critic_result["revised"] = revised
        out["steps"]["auto_critic"] = critic_result

        # 5b. image_maker: real AI visual for the post (Gemini writes
        # the prompt, Imagen 3 renders a 1:1 PNG). Clean skip when no
        # key — the text pipeline is never broken by this.
        image_result = {"ok": False, "skipped": True,
                        "reason": "no visual content produced"}
        if caption.get("ok"):
            image_result = await asyncio.to_thread(
                image_maker.make_post_image, post_text)
        out["steps"]["image_maker"] = image_result

        # 5c. instagram_publisher: real Meta Graph API two-step photo
        # publish. Needs IG_ACCESS_TOKEN + IG_USER_ID AND a PUBLIC
        # https image URL (IMAGE_PUBLIC_URL) — Meta's servers fetch the
        # image themselves, so a local file can never work. All three
        # missing -> honest skip, never a faked post.
        ig_result = {"ok": False, "skipped": True,
                     "reason": "no image available for Instagram"}
        if image_result.get("ok"):
            image_url = (os.environ.get("IMAGE_PUBLIC_URL") or "").strip()
            if image_url:
                ig_result = await asyncio.to_thread(
                    instagram_publisher.publish, image_url, post_text)
            else:
                ig_result = {"ok": False, "skipped": True,
                             "reason": ("IMAGE_PUBLIC_URL not set — upload "
                                        "the generated image somewhere "
                                        "public first (see README 'The "
                                        "public-URL bridge'), then set it. "
                                        "Nothing was published.")}
        out["steps"]["instagram_publisher"] = ig_result

        # 6. scheduler queues the final post (real queue.json write)
        scheduled = None
        published = {"ok": False, "skipped": True,
                     "reason": "no publishable content was produced"}
        if caption.get("ok"):
            scheduled = self.scheduler.schedule_post(
                post_text, channel="telegram")
            # 7. telegram_publisher tries every due post (real API or
            #    clean skip when no token is configured)
            for post in self.scheduler.due_posts():
                published = await asyncio.to_thread(
                    telegram_publish, post["text"])
                if published.get("ok"):
                    self.scheduler.mark_sent(
                        post["id"], published.get("message_id"))
                else:
                    break  # failure/skip: leave it queued, stay honest
        out["steps"]["scheduler"] = {"ok": True, "scheduled": scheduled}
        out["steps"]["telegram_publisher"] = published

        # 8. learning hook: record the mission outcome so future
        #    learn_from_feedback() calls have real material to learn from.
        self.learning.record_mission({
            "mission": mission,
            "niche": niche,
            "critic_passed": critic_result.get("passed"),
            "critic_score": critic_result.get("score"),
            "critic_mode": critic_result.get("mode"),
            "revised": revised,
            "scheduled_id": (scheduled or {}).get("id"),
            "telegram_ok": published.get("ok"),
            "telegram_skipped": published.get("skipped", False),
            "image_ok": image_result.get("ok", False),
            "image_skipped": image_result.get("skipped", False),
            "instagram_ok": ig_result.get("ok", False),
            "instagram_skipped": ig_result.get("skipped", False),
        })

        out["ok"] = True
        return out


async def demo():
    """One mission end-to-end. AI robots need OPENAI_API_KEY; Telegram
    needs its token. With no keys at all the run still completes —
    critic and learning fall back honestly instead of crashing."""
    bot = SuperRobot()
    result = await bot.run_mission(
        mission="Grow a Persian travel audience on Instagram and Telegram "
                "for Victoria BC tours",
        niche="Victoria BC travel",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    asyncio.run(demo())
