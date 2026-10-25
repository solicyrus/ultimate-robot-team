"""ULTIMATE ROBOT TEAM — content_factory/librarian.py

Content Factory robot 20 of 20: the librarian.

Keeps the factory's ledger — content_factory/ledger.jsonl, one JSON
line per concept the factory ever produced (passed OR rejected,
with scores and the gate's notes). The idea generator reads the
recent concepts from here so the factory never repeats itself, and
the rejections become the factory's lessons: what the gate killed,
and why.

Pure file work — no AI, no network. Never raises.
"""

import json
import os
from datetime import datetime

LEDGER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "ledger.jsonl")


def record(entry):
    """Append one outcome to the ledger. Returns True/False."""
    try:
        row = {"time": datetime.now().isoformat()}
        if isinstance(entry, dict):
            row.update(entry)
        else:
            row["summary"] = str(entry)[:1000]
        with open(LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def _read_all():
    rows = []
    try:
        if os.path.isfile(LEDGER_PATH):
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
    except Exception:
        pass
    return rows


def seen_concepts(limit=50):
    """Recent concept summaries (newest last) — the avoid-list the
    idea generator must not repeat."""
    out = []
    for row in _read_all()[-limit:]:
        c = str(row.get("concept", "")).strip()
        if c:
            out.append(c)
    return out


def rejection_lessons(limit=8):
    """Recent gate-rejection notes, phrased as lessons for prompts."""
    lessons = []
    for row in _read_all():
        if row.get("status") == "rejected_by_gate":
            for n in row.get("fix_notes", []) or []:
                lessons.append(f"Gate rejection ({row.get('title', '')}): "
                               f"{n}")
    return lessons[-limit:]


def stats():
    rows = _read_all()
    return {
        "total": len(rows),
        "passed": sum(1 for r in rows if r.get("status") == "queued"),
        "rejected": sum(1 for r in rows
                        if r.get("status") == "rejected_by_gate"),
    }


LIBRARIAN_ROBOT = {"record": record, "seen_concepts": seen_concepts,
                   "rejection_lessons": rejection_lessons, "stats": stats}
