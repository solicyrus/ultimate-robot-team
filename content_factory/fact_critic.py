"""ULTIMATE ROBOT TEAM — content_factory/fact_critic.py

Content Factory robot 17 of 20: the fact critic — the honesty guard.

Two layers of checking over every text that would reach the public:
1. A deterministic scan (no AI): any money amount other than the
   approved CA$10, any clock time that looks like an opening hour,
   and any phone-number-shaped string is flagged automatically.
2. An AI check against the approved-facts block: invented place
   facts (distances, times, "best/only/first" claims, prices) fail.

If the AI layer is unavailable, the deterministic scan alone
decides and the result says so honestly. A package with ANY flag
cannot pass the quality gate.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import APPROVED_FACTS, role_ask  # noqa: E402

_MONEY = re.compile(r"(CA\$|US\$|\$|CAD|USD)\s?\d[\d.,]*", re.IGNORECASE)
_CLOCK = re.compile(r"\b\d{1,2}(:\d{2})?\s?(am|pm)\b", re.IGNORECASE)
_PHONE = re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")
_APPROVED_MONEY = {"ca$10", "ca$ 10"}


def _scan(texts):
    """Deterministic flags over a {field: text} dict."""
    flags = []
    for field, text in (texts or {}).items():
        t = str(text or "")
        for m in _MONEY.finditer(t):
            token = re.sub(r"\s+", " ", m.group(0).strip().lower())
            if token not in _APPROVED_MONEY and not token.startswith("ca$10"):
                flags.append(f"{field}: unapproved money amount "
                             f"'{m.group(0).strip()}'")
        for m in _CLOCK.finditer(t):
            flags.append(f"{field}: clock time '{m.group(0).strip()}' "
                         "looks like an invented hour/schedule")
        for m in _PHONE.finditer(t):
            flags.append(f"{field}: phone-number-shaped string "
                         f"'{m.group(0).strip()}'")
    return flags


_SYSTEM = (
    "You are the FACT CRITIC of a travel content team — the honesty "
    "guard. You hunt for any statement of fact that was not given: "
    "invented prices, hours, distances, dates, statistics, or "
    "'best/only/first in the world' claims about places. "
    + APPROVED_FACTS + " Reply with ONLY valid JSON, no other text."
)


def check_facts(texts):
    """Return {"ok": True, "passed": bool, "flags": [...],
    "ai_used": bool}. texts: {field_name: text}."""
    flags = _scan(texts)
    joined = "\n".join(f"{k}: {v}" for k, v in (texts or {}).items()
                       if str(v or "").strip())
    ai_used = False
    if joined:
        prompt = (
            "Check these draft texts for INVENTED facts (anything "
            "stated as fact that is not in the approved facts and "
            "is not a general visual/emotional description):\n"
            + joined[:3000] + "\n"
            'Reply ONLY valid JSON: {"passed": true, "flags": '
            '["field: problem", ...]} — passed=false if ANY '
            "invented fact is present."
        )
        data = role_ask(_SYSTEM, prompt, max_tokens=500, temperature=0.2)
        if data is not None:
            ai_used = True
            for f in data.get("flags", []):
                f = str(f).strip()
                if f:
                    flags.append(f)
            if data.get("passed") is False and not data.get("flags"):
                flags.append("fact critic AI verdict: failed "
                             "(no specific flag given)")
    return {"ok": True, "ai_used": ai_used,
            "passed": len(flags) == 0, "flags": flags}


FACT_CRITIC_ROBOT = {"check_facts": check_facts}
