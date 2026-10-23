"""ULTIMATE ROBOT TEAM — brain/learning.py

The LearningBrain: the team's ability to get smarter over time.

Adapted from Cyrus's SuperMarketingAgent reference pattern
(original/SuperMarketingAgent.py): a feedback loop where human (or
system) feedback becomes durable lessons that are injected into all
future content prompts.

How it works:
- learn_from_feedback(post, feedback, is_positive):
    * positive -> the post is stored in successful_posts (a win to repeat)
    * negative -> an LLM distills the feedback into a 1-2 sentence RULE
      ("keep captions under 150 words and end with hashtags"), which is
      appended to lessons_learned
  Every call saves to learning_memory.json immediately.
- get_lessons() -> the lesson list, injected into future content prompts
  (see robots/content_robots.py caption_writer) so the team stops
  repeating the same mistakes.
- record_mission(summary) -> stores a mission outcome hook so a human
  can later call learn_from_feedback() on any mission's result.

LLM backend: tries Google Gemini (GEMINI_API_KEY, gemini-2.5-flash) FIRST;
falls back to the team's own brain/llm.py (OpenAI). With NO keys at all,
negative feedback is still stored (marked as raw, not yet distilled)
instead of being lost.

Never raises. Keys come from the environment only, never logged.
"""

import json
import os
from datetime import datetime

DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "learning_memory.json",
)

GEMINI_MODEL = "gemini-2.5-flash"


def _gemini_ask(prompt, system=""):
    """Try Gemini. Returns text or None. Never raises."""
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None
    try:
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system, temperature=0.5),
        )
        text = (getattr(resp, "text", "") or "").strip()
        return text or None
    except Exception:
        return None


def _llm_ask(prompt, system=""):
    """Gemini first, then the team's OpenAI brain. Returns text or None.
    Never raises."""
    try:
        text = _gemini_ask(prompt, system)
        if text:
            return text, "gemini"
        from brain.llm import ask as openai_ask
        text, ok = openai_ask(prompt, system, max_tokens=300,
                              temperature=0.5)
        if ok and text:
            return text, "openai"
        return None, None
    except Exception:
        return None, None


class LearningBrain:
    """Feedback-loop learning with JSON-persisted memory."""

    def __init__(self, path=None):
        self.path = os.path.abspath(path or DEFAULT_PATH)
        self.lessons_learned = []    # list of lesson strings
        self.successful_posts = []   # list of {"post","time"}
        self.mission_log = []        # list of mission outcome hooks
        self._load()

    def _load(self):
        try:
            if os.path.isfile(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.lessons_learned = \
                        data.get("lessons_learned", []) or []
                    self.successful_posts = \
                        data.get("successful_posts", []) or []
                    self.mission_log = data.get("mission_log", []) or []
        except Exception:
            self.lessons_learned, self.successful_posts = [], []
            self.mission_log = []

    def _save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {"lessons_learned": self.lessons_learned[-200:],
                     "successful_posts": self.successful_posts[-200:],
                     "mission_log": self.mission_log[-200:]},
                    f, ensure_ascii=False, indent=2,
                )
            os.replace(tmp, self.path)
        except Exception:
            pass

    def get_lessons(self):
        """Lesson strings for prompt injection into future content."""
        return list(self.lessons_learned)

    def learn_from_feedback(self, post, feedback, is_positive):
        """Learn from one piece of feedback. Never raises.

        Returns {"ok": True, "learned": "success_stored" | "lesson",
                 "lesson": str|None, "backend": "gemini"|"openai"|None}.
        """
        try:
            post_text = str(post or "")[:2000]
            if is_positive:
                self.successful_posts.append(
                    {"post": post_text,
                     "time": datetime.now().isoformat()})
                self._save()
                return {"ok": True, "learned": "success_stored",
                        "lesson": None, "backend": None}

            # Negative feedback: distill it into a reusable rule.
            prompt = (
                "A social-media post received this criticism:\n"
                f"POST: {post_text}\n"
                f"CRITICISM: {feedback}\n\n"
                "In ONE or TWO short sentences, state the exact rule the "
                "writer must follow from now on so this mistake never "
                "repeats. Reply with ONLY the rule, no other text."
            )
            system = ("You turn marketing feedback into short, durable "
                      "writing rules.")
            rule, backend = _llm_ask(prompt, system)
            if rule:
                lesson = rule.strip()
                distilled = True
            else:
                # No LLM available: keep the raw feedback honestly marked
                # instead of losing it. It still gets injected into prompts.
                lesson = ("Raw feedback (not yet distilled into a rule): "
                          + str(feedback).strip())
                distilled = False
                backend = None
            self.lessons_learned.append(lesson)
            self._save()
            return {"ok": True, "learned": "lesson",
                    "lesson": lesson, "backend": backend,
                    "distilled": distilled}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def record_mission(self, summary):
        """Store a mission outcome hook for later feedback.

        summary: dict like {"mission":..., "critic_passed":..., "published":...}.
        A human (or a future auto-evaluator) can call learn_from_feedback()
        on any logged mission.
        """
        try:
            entry = {"time": datetime.now().isoformat()}
            if isinstance(summary, dict):
                entry.update(summary)
            else:
                entry["summary"] = str(summary)[:1000]
            self.mission_log.append(entry)
            self._save()
            return True
        except Exception:
            return False
