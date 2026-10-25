"""ULTIMATE ROBOT TEAM — robots/runner.py

The execution loop: turns the content factory into a complete
social-media machine WITH HUMAN APPROVAL.

The daily workflow:
    1. prepare  -> queue.json posts move into approval_queue.json
                  with a full preview (caption + AI image, or an
                  honest skip when no key). NOTHING is published
                  in this mode.
    2. YOU review:  python approve.py list
    3. approve / reject  (a rejection teaches the team a lesson via
                         brain/learning.py)
    4. publish  -> approved AND due posts go out via Telegram then
                  Instagram (each a real send or an honest skip).
                  The outcome is recorded for future learning.

Commands (run from the project root):
    python -m robots.runner prepare
    python -m robots.runner publish
    python -m robots.runner status

NOTHING publishes without an explicit `approve` in approve.py.
Keys come from the environment only. Never raises on I/O problems;
network results are always reported honestly, never faked.
"""

import json
import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.learning import LearningBrain
from robots import image_maker
from robots import instagram_publisher
from robots.scheduler import PostScheduler
from robots.telegram_publisher import publish as telegram_publish

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPROVAL_PATH = os.path.join(PROJECT_ROOT, "approval_queue.json")
IMAGES_DIR = os.path.join(PROJECT_ROOT, "images")

# approval_queue.json statuses
AWAITING = "awaiting_approval"
APPROVED = "approved"
REJECTED = "rejected"
PUBLISHED = "published"
PARTIAL = "partial"

# queue.json statuses the runner picks up for preparation
PREPARE_SOURCES = ("queued", "scheduled")


class ApprovalQueue:
    """approval_queue.json: posts waiting for — or decided by — the human."""

    def __init__(self, path=None):
        self.path = os.path.abspath(path or APPROVAL_PATH)
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

    def add(self, entry):
        self.posts.append(entry)
        self._save()
        return entry

    def find(self, post_id):
        """Exact id match, then unique-prefix match.
        Returns (entry, None) or (None, error_message)."""
        pid = (post_id or "").strip()
        if not pid:
            return None, "empty post id"
        exact = [p for p in self.posts if p.get("id") == pid]
        if exact:
            return exact[0], None
        pref = [p for p in self.posts
                if str(p.get("id", "")).startswith(pid)]
        if len(pref) == 1:
            return pref[0], None
        if len(pref) > 1:
            return None, f"ambiguous id {pid!r}: matches {len(pref)} posts"
        return None, f"unknown post id {pid!r}"

    def set_status(self, post_id, status, **extra):
        entry, err = self.find(post_id)
        if err:
            return False
        entry["status"] = status
        entry.update(extra)
        self._save()
        return True

    def by_status(self, status):
        return [p for p in self.posts if p.get("status") == status]

    def all(self):
        return list(self.posts)


class Runner:
    """The execution loop. Every step does real work or reports an
    honest failure — nothing is simulated, nothing publishes without
    human approval."""

    def __init__(self):
        self.scheduler = PostScheduler()
        self.approval = ApprovalQueue()
        self.learning = LearningBrain()

    # -- prepare ------------------------------------------------------
    def cmd_prepare(self):
        """Move unprepared queue posts into the approval queue with a
        full preview (caption + AI image or honest skip). Never
        publishes anything."""
        try:
            os.makedirs(IMAGES_DIR, exist_ok=True)
        except Exception:
            pass
        image_public_url = ((os.environ.get("IMAGE_PUBLIC_URL") or "")
                            .strip() or None)

        self.scheduler = PostScheduler()  # fresh read
        sources = [p for p in self.scheduler.posts
                   if p.get("status") in PREPARE_SOURCES]
        candidates = [p for p in sources if (p.get("text") or "").strip()]
        skipped_no_caption = len(sources) - len(candidates)

        ids = []
        for post in candidates:
            text = post["text"].strip()
            pid = uuid.uuid4().hex[:8]
            img_path = os.path.join(IMAGES_DIR, pid + ".png")
            img = image_maker.make_post_image(text, output_path=img_path)
            entry = {
                "id": pid,
                "source_id": post.get("id"),
                "caption": text,
                "image_path": img.get("path") if img.get("ok") else None,
                "image_note": (None if img.get("ok")
                               else (img.get("reason") or img.get("error"))),
                "image_public_url": image_public_url,
                "scheduled_for": (post.get("when")
                                  or datetime.now().isoformat()),
                "created_at": datetime.now().isoformat(),
                "status": AWAITING,
                "channels": ["telegram", "instagram"],
                "results": {},
            }
            self.approval.add(entry)
            self.scheduler.mark_prepared(post.get("id"))
            ids.append(pid)
        return {"ok": True, "prepared": len(ids), "ids": ids,
                "skipped_no_caption": skipped_no_caption}

    # -- publish ------------------------------------------------------
    def cmd_publish(self, now=None):
        """Publish approved + due posts: Telegram first, then
        Instagram. Each channel reports a real send or an honest
        skip. Outcomes are recorded for future learning."""
        now = now or datetime.now().isoformat()
        due = [e for e in self.approval.all()
               if e.get("status") == APPROVED
               and (e.get("scheduled_for") or "") <= now]
        published = []
        for e in due:
            caption = e.get("caption", "")
            tg = telegram_publish(caption)
            ig_url = ((e.get("image_public_url") or "").strip()
                      or (os.environ.get("IMAGE_PUBLIC_URL") or "").strip())
            ig = instagram_publisher.publish(ig_url, caption)
            results = {"telegram": tg, "instagram": ig}
            status = (PUBLISHED if (tg.get("ok") and ig.get("ok"))
                      else PARTIAL)
            self.approval.set_status(
                e["id"], status, results=results,
                published_at=datetime.now().isoformat())
            self.learning.record_mission({
                "runner_publish": True,
                "post_id": e["id"],
                "status": status,
                "telegram_ok": bool(tg.get("ok")),
                "telegram_skipped": bool(tg.get("skipped", False)),
                "instagram_ok": bool(ig.get("ok")),
                "instagram_skipped": bool(ig.get("skipped", False)),
            })

            def _ch(r):
                return ("ok" if r.get("ok")
                        else ("skipped" if r.get("skipped") else "failed"))
            published.append({"id": e["id"], "status": status,
                              "telegram": _ch(tg), "instagram": _ch(ig)})
        return {"ok": True, "published": len(published), "posts": published}

    # -- status -------------------------------------------------------
    def cmd_status(self):
        """Machine-readable summary for the status command."""
        counts = {}
        for e in self.approval.all():
            s = e.get("status", "?")
            counts[s] = counts.get(s, 0) + 1
        q = PostScheduler()  # fresh read
        qcounts = {}
        for p in q.posts:
            s = p.get("status", "?")
            qcounts[s] = qcounts.get(s, 0) + 1
        now = datetime.now().isoformat()
        due = [e for e in self.approval.all()
               if e.get("status") == APPROVED
               and (e.get("scheduled_for") or "") <= now]
        due_sorted = sorted(due, key=lambda e: e.get("scheduled_for", ""))
        return {"approval_queue": counts, "queue_json": qcounts,
                "due_now": len(due),
                "next_due_id": due_sorted[0]["id"] if due_sorted else None}


_LABELS = {
    "awaiting_approval": "در انتظار تأیید شما / awaiting your approval",
    "approved": "تأیید شده / approved (ready to publish)",
    "rejected": "رد شده / rejected",
    "published": "منتشر شده / published",
    "partial": "ناقص / partial (a channel failed or was skipped)",
}


def _print_status(s):
    print("== Approval queue ==")
    if s["approval_queue"]:
        for st, n in sorted(s["approval_queue"].items()):
            print(f"  {_LABELS.get(st, st)}: {n}")
    else:
        print("  (empty — nothing prepared yet)")
    print(f"Due for publishing now: {s['due_now']}")
    if s["next_due_id"]:
        print(f"Next due post id: {s['next_due_id']}")
    print("== queue.json ==")
    if s["queue_json"]:
        for st, n in sorted(s["queue_json"].items()):
            print(f"  {st}: {n}")
    else:
        print("  (empty)")


def main(argv):
    if len(argv) < 2 or argv[1] not in ("prepare", "publish", "status"):
        print("Usage: python -m robots.runner <prepare|publish|status>",
              file=sys.stderr)
        return 2
    try:
        runner = Runner()
        cmd = argv[1]
        if cmd == "prepare":
            r = runner.cmd_prepare()
            ids = ", ".join(r["ids"]) if r["ids"] else "none"
            print(f"prepared {r['prepared']} post(s) for your review "
                  f"(ids: {ids})")
            if r["skipped_no_caption"]:
                print(f"skipped {r['skipped_no_caption']} post(s) "
                      "with no caption")
            print("Nothing was published. "
                  "Review with: python approve.py list")
        elif cmd == "publish":
            r = runner.cmd_publish()
            if not r["posts"]:
                print("Nothing due for publishing.")
            for p in r["posts"]:
                print(f"{p['id']}: {p['status']} "
                      f"(telegram: {p['telegram']}, "
                      f"instagram: {p['instagram']})")
        else:
            _print_status(runner.cmd_status())
        return 0
    except Exception as e:  # never a traceback for the human
        print(f"runner failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
