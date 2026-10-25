"""ULTIMATE ROBOT TEAM — content_factory/fact_critic.py

Content Factory robot 17 of 20: the fact critic — the honesty guard.

THE RULE (architectural decision, 2026-10-25): the DETERMINISTIC
scan is the ONLY hard-fail authority in this module. The AI layer
is WARNINGS ONLY — it still runs, and its complaints are still
reported in "warnings" (they are useful notes for the human
approver), but an AI complaint can NEVER fail a package: it never
sets "passed" to False and never appears in "flags".

Why: the AI layer kept false-flagging the team's own standard
content — first the approved CA$10 price line itself, then the
channel-registry links from brain/channels.py that every
description carries by design. Whitelisting each new case was
whack-a-mole. The deterministic scan has never false-flagged, and
it catches the real dangers — invented prices, hours, phone
numbers — so it alone decides pass/fail.

The two layers:
1. Deterministic scan (no AI): any money amount other than the
   approved CA$10, any clock time that looks like an opening
   hour, and any phone-number-shaped string is flagged,
   quoting the offending token. Matches that fall inside an
   APPROVED-FACT phrase (e.g. the "CA$10" inside "CA$10 for
   14 days") are skipped — they are the approved fact itself,
   not an invention. "flags" holds ONLY this scan's hits, and
   "passed" is True iff "flags" is empty.
2. AI check against the approved-facts block: every complaint —
   quoted or not — lands in "warnings" for the human approver.
   It changes nothing else.

If the AI layer is unavailable, the deterministic scan alone
decides (which it does anyway) and ai_used says so honestly.
Hard flags block the quality gate; warnings never do.
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
# The approved token, strictly: CA$10 with an optional ".00".
# (A bare startswith("ca$10") would also wave through CA$100 —
# an invented price — so the token must match in full.)
_APPROVED_TOKEN = re.compile(r"ca\$\s?10(?:\.0+)?")

# --- APPROVED-FACTS whitelist -------------------------------------
# The ONLY product facts factory content may state (mirrors
# common.APPROVED_FACTS). Used by the deterministic scan to skip
# matches that fall inside an approved-fact phrase, and to
# annotate AI warnings. Premium $79 is NOT here on purpose: it is
# not approved for factory content.
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
    """Deterministic flags over a {field: text} dict — the ONLY
    hard-fail authority. Matches that fall inside an approved-fact
    phrase are skipped; every other price / hour / phone-shaped
    token is caught, quoting the offending token."""
    flags = []
    for field, text in (texts or {}).items():
        t = str(text or "")
        spans = _approved_spans(t)
        for m in _MONEY.finditer(t):
            if _inside(spans, m):
                continue
            token = re.sub(r"\s+", " ", m.group(0).strip().lower())
            token = token.rstrip(".")
            if (token not in _APPROVED_MONEY
                    and not _APPROVED_TOKEN.fullmatch(token)):
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
    (whitespace/case-insensitive), or None. Used only to annotate
    AI warnings — never to fail anything."""
    q = _norm(quote).strip("'\"")
    if len(q) < 3:
        return None
    for field, text in (texts or {}).items():
        if q in _norm(text):
            return field
    return None


def _ai_warnings(data, texts):
    """Turn the AI layer's complaints into WARNINGS — all of them,
    unconditionally. Per the module rule, the AI layer is advisory
    only: nothing it says can hard-fail a package, so every
    complaint is formatted as a note for the human approver. Where
    a complaint carries a quote, the warning says whether that
    quote verifiably appears in a field and whether it is an
    approved fact."""
    warnings = []
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
        label = field if field in _FIELDS else (found or "general")
        note = ""
        if quote and found and _is_approved(quote):
            note = " — this is an approved fact"
        elif quote and not found:
            note = " — quote not found in any field (unverified)"
        warnings.append(
            f"fact critic AI warning ({label}): "
            + (f"'{quote}'" if quote else "")
            + (f" — {claim}" if claim else "")
            + note)
    if data.get("passed") is False:
        warnings.append("fact critic AI verdict: failed "
                        "(warning only — AI verdicts never block)")
    return warnings


def check_facts(texts):
    """Return {"ok": True, "passed": bool, "flags": [...],
    "warnings": [...], "ai_used": bool}. texts: {field: text}.

    "flags" holds ONLY hard failures: deterministic-scan hits
    (which quote the offending token). The AI layer's complaints
    go to "warnings" and can never appear in "flags". "passed"
    is True iff the deterministic scan found nothing.
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
            "Quote precisely — your complaints are advisory notes "
            "for a human approver. General praise, emotions and "
            "visual descriptions are NOT facts.\n"
            'Reply ONLY valid JSON: {"passed": true, "flags": '
            '[{"field": "...", "quote": "...", "claim": "..."}, '
            "...]} — passed=false only if at least one quoted "
            "invented fact is present."
        )
        data = role_ask(_SYSTEM, prompt, max_tokens=600, temperature=0.2)
        if data is not None:
            ai_used = True
            warnings.extend(_ai_warnings(data, texts))
    return {"ok": True, "ai_used": ai_used,
            "passed": len(flags) == 0, "flags": flags,
            "warnings": warnings}


FACT_CRITIC_ROBOT = {"check_facts": check_facts}
