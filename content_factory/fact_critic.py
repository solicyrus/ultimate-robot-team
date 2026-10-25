"""ULTIMATE ROBOT TEAM — content_factory/fact_critic.py

Content Factory robot 17 of 20: the fact critic — the honesty guard.

Two layers of checking over every text that would reach the public:
1. A deterministic scan (no AI): any money amount other than the
   approved CA$10, any clock time that looks like an opening hour,
   and any phone-number-shaped string is flagged automatically.
   These flags quote the offending token and are the hard-fail
   authority. Matches that fall inside an APPROVED-FACT phrase
   (e.g. the "CA$10" inside "CA$10 for 14 days") are skipped —
   they are the approved fact itself, not an invention.
2. An AI check against the approved-facts block. An AI complaint
   only counts as a flag when it carries a CONCRETE QUOTE: the
   exact offending phrase, verified to appear in the named field,
   plus what invented fact that phrase asserts. An AI complaint
   without a verifiable quote is downgraded to a warning — it is
   reported, but it does NOT fail the package.

APPROVED-FACTS WHITELIST (added 2026-10-25): before any AI flag
can hard-fail, its quote is checked against the approved set
below. A flag whose quoted content matches an approved fact is
DISCARDED and logged as a warning ("approved fact, ignored") —
the previous live run hard-flagged the approved price line
itself ("…try Cyrus AI trip planning for just CA$10 for 14
days." — "asserts a price"), which is a plain bug: the approved
fact can never be an invented fact. Premium $79 is deliberately
NOT whitelisted — it is not approved for factory content.

If the AI layer is unavailable, the deterministic scan alone
decides and the result says so honestly. A package with ANY hard
flag cannot pass the quality gate; warnings never block it.
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

# --- APPROVED-FACTS whitelist -------------------------------------
# The ONLY product facts factory content may state (mirrors
# common.APPROVED_FACTS). A flag — AI or scan — whose quoted
# content matches one of these is the approved fact itself, NOT
# an invented fact, and must never hard-fail. Premium $79 is NOT
# here on purpose: it is not approved for factory content.
_APPROVED_SPAN_RES = (
    re.compile(r"ca\$\s?10\s+for\s+14\s+days", re.IGNORECASE),
    re.compile(r"cyrus\s+ai\s+trip\s+planning\s+costs\s+ca\$\s?10",
               re.IGNORECASE),
    re.compile(r"victoriatourandadventure\.com", re.IGNORECASE),
    re.compile(r"cyrus\s+ai\s+tour\s+guide", re.IGNORECASE),
    re.compile(r"google\s+play", re.IGNORECASE),
)
# Normalised (lowercase, single-spaced) distinctive phrases for
# quote matching in _is_approved.
_APPROVED_NORM = (
    "ca$10 for 14 days",
    "ca$ 10 for 14 days",
    "cyrus ai trip planning costs ca$10",
    "victoriatourandadventure.com",
    "cyrus ai tour guide",
    "google play",
)


def _approved_spans(text):
    """Character spans of `text` covered by an approved-fact
    phrase (case-insensitive)."""
    spans = []
    for rx in _APPROVED_SPAN_RES:
        spans.extend(m.span() for m in rx.finditer(text))
    return spans


def _inside(spans, match):
    return any(a <= match.start() and match.end() <= b
               for a, b in spans)


def _is_approved(quote):
    """True when a quoted phrase IS (part of) an approved fact —
    e.g. the whole approved price line, or the bare "CA$10" token
    lifted from inside it."""
    q = _norm(quote).strip("'\"")
    if not q:
        return False
    if q in _APPROVED_MONEY:
        return True
    return any(p in q or (len(q) >= 6 and q in p)
               for p in _APPROVED_NORM)


def _scan(texts):
    """Deterministic flags over a {field: text} dict. Matches that
    fall inside an approved-fact phrase are skipped; every other
    price / hour / phone-shaped token is still caught."""
    flags = []
    for field, text in (texts or {}).items():
        t = str(text or "")
        spans = _approved_spans(t)
        for m in _MONEY.finditer(t):
            if _inside(spans, m):
                continue
            token = re.sub(r"\s+", " ", m.group(0).strip().lower())
            if token not in _APPROVED_MONEY and not token.startswith("ca$10"):
                flags.append(f"{field}: unapproved money amount "
                             f"'{m.group(0).strip()}'")
        for m in _CLOCK.finditer(t):
            if _inside(spans, m):
                continue
            flags.append(f"{field}: clock time '{m.group(0).strip()}' "
                         "looks like an invented hour/schedule")
        for m in _PHONE.finditer(t):
            if _inside(spans, m):
                continue
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

_FIELDS = ("hook", "title", "caption", "description", "script")
_QUOTED = re.compile(r"['\"]([^'\"]{3,})['\"]")


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "").lower()).strip()


def _quote_field(quote, texts):
    """Return the field whose text actually contains the quote
    (whitespace/case-insensitive), or None. A quote that appears
    nowhere is not evidence of anything."""
    q = _norm(quote).strip("'\"")
    if len(q) < 3:
        return None
    for field, text in (texts or {}).items():
        if q in _norm(text):
            return field
    return None


def _ai_flags(data, texts):
    """Split the AI layer's complaints into (hard flags, warnings).

    A complaint becomes a HARD flag only when it carries a concrete
    quote that verifiably appears in one of the checked fields AND
    the quote does not match the approved-facts whitelist. A
    verified quote that IS an approved fact is discarded with an
    "approved fact, ignored" warning. Anything else is a warning:
    reported, never blocking.
    """
    hard, warnings = [], []
    for raw in data.get("flags", []) or []:
        field = quote = claim = ""
        if isinstance(raw, dict):
            field = str(raw.get("field", "")).strip().lower()
            quote = str(raw.get("quote", "")).strip()
            claim = str(raw.get("claim", "")
                        or raw.get("problem", "")).strip()
        else:
            text = str(raw).strip()
            if not text:
                continue
            head, _, rest = text.partition(":")
            if head.strip().lower() in _FIELDS:
                field, claim = head.strip().lower(), rest.strip()
            else:
                claim = text
            m = _QUOTED.search(text)
            if m:
                quote = m.group(1).strip()
        if not claim and not quote:
            continue
        found = _quote_field(quote, texts) if quote else None
        if found and _is_approved(quote):
            # The quote verifiably appears in a field, but it IS
            # an approved fact — it can never be an invented
            # fact. Discard the flag; log it as a warning.
            label = field if field in _FIELDS else found
            warnings.append(
                f"fact critic AI ({label}): '{quote}' — "
                "approved fact, ignored")
        elif found:
            label = field if field in _FIELDS else found
            hard.append(f"{label}: invented fact '{quote}'"
                        + (f" — asserts {claim}" if claim else ""))
        else:
            warnings.append("fact critic AI (unverified — no "
                            "concrete quote): "
                            + (f"{field}: " if field else "")
                            + (claim or quote))
    if data.get("passed") is False and not hard:
        warnings.append("fact critic AI verdict: failed, but it "
                        "quoted no concrete invented fact "
                        "(warning only)")
    return hard, warnings


def check_facts(texts):
    """Return {"ok": True, "passed": bool, "flags": [...],
    "warnings": [...], "ai_used": bool}. texts: {field: text}.

    "flags" holds ONLY hard failures: deterministic-scan hits (which
    quote the offending token) and AI complaints backed by a
    verified concrete quote. "passed" is True iff flags is empty.
    """
    flags = _scan(texts)
    warnings = []
    joined = "\n".join(f"{k}: {v}" for k, v in (texts or {}).items()
                       if str(v or "").strip())
    ai_used = False
    if joined:
        prompt = (
            "Check these draft texts for INVENTED facts (anything "
            "stated as fact that is not in the approved facts and "
            "is not a general visual/emotional description):\n"
            + joined[:3000] + "\n"
            "For EVERY problem you find you MUST give:\n"
            "- field: which field it is in (hook, title, caption, "
            "description or script);\n"
            "- quote: the EXACT offending phrase, copied word for "
            "word from that field;\n"
            "- claim: the invented fact that phrase asserts (a "
            "price, hour, phone number, distance, date or place "
            "fact that was not given).\n"
            "A complaint without an exact quote is ignored, so "
            "quote precisely or do not raise it. General praise, "
            "emotions and visual descriptions are NOT facts.\n"
            'Reply ONLY valid JSON: {"passed": true, "flags": '
            '[{"field": "...", "quote": "...", "claim": "..."}, '
            "...]} — passed=false only if at least one quoted "
            "invented fact is present."
        )
        data = role_ask(_SYSTEM, prompt, max_tokens=600, temperature=0.2)
        if data is not None:
            ai_used = True
            hard, warns = _ai_flags(data, texts)
            for f in hard:
                if f not in flags:
                    flags.append(f)
            warnings.extend(warns)
    return {"ok": True, "ai_used": ai_used,
            "passed": len(flags) == 0, "flags": flags,
            "warnings": warnings}


FACT_CRITIC_ROBOT = {"check_facts": check_facts}
