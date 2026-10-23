"""ULTIMATE ROBOT TEAM — brain/memory.py

Real persisted memory. Everything is saved to brain_memory.json on disk,
so the team remembers across runs. (The skeleton's "memory" was a Python
deque that vanished the moment the program stopped.)

- remember(key, value, important=False): store it now, save the file now.
- recall(key): get a stored value, or None if never stored.
- recent(n=10): the last n short-term entries.
- important(): everything marked important (long-term).
- Never raises: a missing or corrupt file simply starts fresh memory
  instead of crashing the team.
"""

import json
import os
from datetime import datetime

DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "brain_memory.json",
)


class BrainMemory:
    def __init__(self, path=None):
        self.path = os.path.abspath(path or DEFAULT_PATH)
        self.short_term = []  # list of {"key","value","time"}
        self.long_term = {}   # key -> {"value","time"}
        self._load()

    def _load(self):
        try:
            if os.path.isfile(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.short_term = data.get("short_term", []) or []
                    self.long_term = data.get("long_term", {}) or {}
        except Exception:
            self.short_term, self.long_term = [], {}

    def _save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {"short_term": self.short_term[-500:],
                     "long_term": self.long_term},
                    f, ensure_ascii=False, indent=2,
                )
            os.replace(tmp, self.path)
        except Exception:
            pass

    def remember(self, key, value, important=False):
        """Store a memory and persist it to disk immediately."""
        entry = {"key": key, "value": value,
                 "time": datetime.now().isoformat()}
        self.short_term.append(entry)
        if important:
            self.long_term[key] = {"value": value, "time": entry["time"]}
        self._save()
        return True

    def recall(self, key):
        """Return a stored value, or None."""
        if key in self.long_term:
            return self.long_term[key]["value"]
        for entry in reversed(self.short_term):
            if entry["key"] == key:
                return entry["value"]
        return None

    def recent(self, n=10):
        """Last n short-term memories, oldest first."""
        return self.short_term[-n:]

    def important(self):
        """All long-term (important) memories as {key: value}."""
        return {k: v["value"] for k, v in self.long_term.items()}
