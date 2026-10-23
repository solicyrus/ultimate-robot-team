"""ULTIMATE ROBOT TEAM — brain/critic.py

The AutoCritic: robot #10. Before any post goes to the queue, the critic
plays "strict editor" and checks it against the team's standards.

Standards checked:
  1. Honest claims only — no invented prices, phone numbers, addresses,
     or facts the team was not given.
  2. Persian AND English caption present.
  3. Ends with hashtags.
  4. Adventurous, energetic tone (not boring/flat).
  5. Has a call-to-action (link in bio, DM, book, ...).

review(draft) -> {"ok": True, "passed": bool, "score": 1-10,
                   "issues": [...], "suggestion": "...",
                   "mode": "ai" | "rule-based"}

With the AI available, a real LLM judges the draft. With NO key at all,
a deterministic rule-based check runs instead (hashtags present? CTA
present? both languages present? sane length?) — weaker than the AI,
but honest about what it is. Never raises, never fakes a pass.
"""

import re

_STANDARDS = (
    "You are a strict social-media editor. Judge the draft post below "
    "against these 5 standards:\n"
    "1. HONESTY: no invented prices, phone numbers, addresses, or facts.\n"
    "2. BILINGUAL: the post must contain BOTH a Persian and an English part.\n"
    "3. HASHTAGS: the post must end with hashtags (#...).\n"
    "4. TONE: adventurous and energetic, not flat or boring.\n"
    "5. CTA: must contain a call-to-action (link in bio, DM us, book now, "
    "visit, ...).\n"
    "Reply with ONLY valid JSON, no other text:\n"
    '{"passed": true/false, "score": 1-10, '
    '"issues": ["short issue 1", ...], '
    '"suggestion": "one concrete paragraph telling the writer exactly '
    'how to fix every issue"}'
)

_CTA_MARKERS = ("http", "لینک", "دایرکت", "dm", "رزرو", "book", "bio",
                "ثبت", "کلیک", "click", "سفارش", "پیام", "تماس",
                "call", "visit", "join")


def _has_persian(text):
    return bool(re.search(r"[\u0600-\u06FF]", text or ""))


def _has_english(text):
    return bool(re.search(r"[A-Za-z]{3,}", text or ""))


def _has_hashtags(text):
    return bool(re.search(r"#\S+", text or ""))


def _ends_with_hashtags(text):
    tail = (text or "").strip().split("\n")[-1]
    return "#" in tail


def _has_cta(text):
    low = (text or "").lower()
    return any(m in low for m in _CTA_MARKERS)


def _rule_based_review(draft):
    """Deterministic fallback when no AI key exists. Honest, limited."""
    issues = []
    if not _has_persian(draft):
        issues.append("missing Persian part")
    if not _has_english(draft):
        issues.append("missing English part")
    if not _has_hashtags(draft):
        issues.append("no hashtags at all")
    elif not _ends_with_hashtags(draft):
        issues.append("hashtags present but post does not end with them")
    if not _has_cta(draft):
        issues.append("no call-to-action found")
    n = len(draft or "")
    if n < 30:
        issues.append("post is too short to be useful")
    elif n > 2200:
        issues.append("post is too long for social media")

    checks = 6
    failed = len(issues)
    score = max(1, round(10 * (checks - failed) / checks))
    # Critical gates: a post without hashtags or CTA never passes.
    passed = (_has_hashtags(draft) and _has_cta(draft)
              and _has_persian(draft) and _has_english(draft))

    if issues:
        suggestion = ("Fix these issues before publishing: "
                      + "; ".join(issues) + ".")
    else:
        suggestion = "Post meets all standards."
    return {"ok": True, "passed": passed, "score": score,
            "issues": issues, "suggestion": suggestion,
            "mode": "rule-based", "ai_used": False}


class AutoCritic:
    """Strict editor for drafts. AI when available, rules when not."""

    def review(self, draft):
        """Review one draft post. Never raises."""
        try:
            draft = str(draft or "")
            if not draft.strip():
                return {"ok": False, "passed": False, "score": 1,
                        "issues": ["empty draft"],
                        "suggestion": "Write the post first.",
                        "mode": "rule-based", "ai_used": False}

            # Try the real AI judge first.
            try:
                from brain.llm import ask_json
                data, ai_used = ask_json(
                    "DRAFT POST TO JUDGE:\n" + draft,
                    _STANDARDS, max_tokens=500, temperature=0.3)
            except Exception:
                data, ai_used = None, False

            if ai_used and isinstance(data, dict):
                passed = bool(data.get("passed", False))
                try:
                    score = int(data.get("score", 5))
                except (TypeError, ValueError):
                    score = 5
                score = max(1, min(10, score))
                issues = data.get("issues", []) or []
                issues = [str(i) for i in issues][:8]
                suggestion = str(data.get("suggestion", ""))[:800]
                return {"ok": True, "passed": passed, "score": score,
                        "issues": issues, "suggestion": suggestion,
                        "mode": "ai", "ai_used": True}

            # No AI: honest deterministic fallback.
            return _rule_based_review(draft)
        except Exception as e:
            return {"ok": False, "passed": False, "score": 1,
                    "issues": ["critic crashed: " + str(e)[:120]],
                    "suggestion": "Fix the critic before trusting it.",
                    "mode": "rule-based", "ai_used": False}
