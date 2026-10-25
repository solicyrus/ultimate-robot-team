"""ULTIMATE ROBOT TEAM — approve.py

The HUMAN APPROVAL GATE. Nothing publishes without an explicit
approve here.

Usage (run from the project root):
    python approve.py list                       # show posts awaiting
                                                 # your review, with previews
    python approve.py <post_id> approve          # approve -> publishable
    python approve.py <post_id> reject "note"    # reject AND teach the
                                                 # team: the note becomes
                                                 # a durable lesson

A post id can be given in full or as a unique starting prefix.
Unknown ids and wrong states are clean errors (no tracebacks).
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain.learning import LearningBrain
from robots.runner import (ApprovalQueue, AWAITING, APPROVED, REJECTED)

USAGE = """Usage:
  python approve.py list
  python approve.py <post_id> approve
  python approve.py <post_id> reject "your note\""""


def _preview(text, n=150):
    t = " ".join((text or "").split())
    return t[:n] + ("..." if len(t) > n else "")


def cmd_list(q):
    waiting = q.by_status(AWAITING)
    if not waiting:
        print("Nothing awaiting your approval. 🎉")
        return 0
    print(f"{len(waiting)} post(s) awaiting your approval:\n")
    for e in waiting:
        print(f"  id:            {e['id']}")
        print(f"  scheduled for: {e.get('scheduled_for')}")
        img = e.get("image_path")
        print(f"  image:         {'yes -> ' + img if img else 'no (skipped)'}")
        print(f"  caption:       {_preview(e.get('caption'))}")
        print()
    print("Approve:  python approve.py <id> approve")
    print('Reject:   python approve.py <id> reject "your note"')
    return 0


def _get_awaiting(q, pid):
    e, err = q.find(pid)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return None
    if e.get("status") != AWAITING:
        print(f"error: post {e['id']} is '{e.get('status')}', "
              "not awaiting approval", file=sys.stderr)
        return None
    return e


def cmd_approve(q, pid):
    e = _get_awaiting(q, pid)
    if e is None:
        return 2
    q.set_status(e["id"], APPROVED,
                 approved_at=datetime.now().isoformat())
    print(f"approved {e['id']} ✅ — it will go out on the next publish run")
    return 0


def cmd_reject(q, pid, note):
    e = _get_awaiting(q, pid)
    if e is None:
        return 2
    q.set_status(e["id"], REJECTED, reject_note=note,
                 rejected_at=datetime.now().isoformat())
    lb = LearningBrain()
    res = lb.learn_from_feedback(e.get("caption", ""), note,
                                 is_positive=False)
    print(f"rejected {e['id']}")
    if res.get("ok") and res.get("lesson"):
        print(f"🧠 the team learned and will apply it next time:\n"
              f"   {res['lesson']}")
    else:
        print("your note was recorded for the team")
    return 0


def main(argv):
    try:
        q = ApprovalQueue()
    except Exception as e:
        print(f"error: cannot read the approval queue: {e}",
              file=sys.stderr)
        return 1
    if len(argv) < 2:
        print(USAGE, file=sys.stderr)
        return 2
    if argv[1].lower() == "list":
        return cmd_list(q)
    # form: <post_id> <approve|reject> [note...]
    pid = argv[1]
    if len(argv) < 3:
        print(USAGE, file=sys.stderr)
        return 2
    action = argv[2].lower()
    if action == "approve":
        return cmd_approve(q, pid)
    if action == "reject":
        note = " ".join(argv[3:]).strip() or "rejected without a note"
        return cmd_reject(q, pid, note)
    print(f"error: unknown action {action!r}\n{USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
