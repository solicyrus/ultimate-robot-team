"""ULTIMATE ROBOT TEAM — robots/scheduler.py

A REAL post queue stored in queue.json on disk (survives restarts).

- schedule_post(text, when=None, channel="telegram") -> the queued post.
  `when` is an ISO datetime string; None means "post as soon as possible".
- due_posts(now=None) -> queued posts whose time has come.
- mark_sent(post_id, message_id=None) -> marks a post sent.
- pending() -> all posts still queued.

Never raises on a missing/corrupt queue file — starts empty instead.
"""

import json
import os
import uuid
from datetime import datetime

DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "queue.json",
)


class PostScheduler:
    def __init__(self, path=None):
        self.path = os.path.abspath(path or DEFAULT_PATH)
        self.posts = []
        self._load()

    def _load(self):
        try:
            if os.path.isfile(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.posts = data
        except Exception:
            self.posts = []

    def _save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.posts, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            pass

    def schedule_post(self, text, when=None, channel="telegram"):
        """Queue a post. Returns the stored post dict (with its id)."""
        post = {
            "id": uuid.uuid4().hex[:8],
            "text": text,
            "when": when or datetime.now().isoformat(),
            "channel": channel,
            "status": "queued",
            "created": datetime.now().isoformat(),
            "message_id": None,
        }
        self.posts.append(post)
        self._save()
        return post

    def due_posts(self, now=None):
        """Queued posts whose scheduled time has arrived (oldest first)."""
        now = now or datetime.now().isoformat()
        due = [p for p in self.posts
               if p.get("status") == "queued" and p.get("when", "") <= now]
        return sorted(due, key=lambda p: p.get("when", ""))

    def mark_sent(self, post_id, message_id=None):
        """Mark a post as sent. Returns True if found."""
        for p in self.posts:
            if p.get("id") == post_id:
                p["status"] = "sent"
                p["message_id"] = message_id
                p["sent_at"] = datetime.now().isoformat()
                self._save()
                return True
        return False

    def pending(self):
        """All posts still waiting in the queue."""
        return [p for p in self.posts if p.get("status") == "queued"]
