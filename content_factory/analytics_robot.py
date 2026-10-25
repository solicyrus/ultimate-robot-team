"""ULTIMATE ROBOT TEAM — content_factory/analytics_robot.py

Content Factory robot 22 of 22: the analytics robot.

Closes the loop the factory was missing: it tracks everything the
team has actually PUBLISHED (approval_queue.json entries carrying
a published URL) and snapshots how each piece is doing, so the
daily rotation is steered by numbers instead of guesses.

For YouTube entries it reads the PUBLIC watch/Shorts page — no
API key, no credentials, nothing private. View and like counts
are parsed only where the page itself exposes them; a count that
cannot be read is recorded as null — this robot NEVER invents a
number (the team's honesty rule). Every run appends one snapshot
row per published entry to content_factory/analytics.jsonl and
prints a short summary: per-entry views / likes / views-per-day,
the totals, and the top performer.

Telegram (and any non-YouTube platform) has no public counts —
those entries are tracked with null stats, URL and date only.

Run it (from the project root):
    ./venv/bin/python -m content_factory.analytics_robot
    ./venv/bin/python -m content_factory.analytics_robot --out /tmp/analytics.jsonl
"""

import json
import os
import re
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from robots.runner import ApprovalQueue  # noqa: E402

ANALYTICS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "analytics.jsonl")

_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
_HEADERS = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}

_VIEW_PATTERNS = (
    r'"viewCount":"(\d+)"',
    r'itemprop="interactionCount" content="(\d+)"',
    r'"simpleText":"([\d,]+) views"',
)
_LIKE_PATTERNS = (
    r'"likeCount":"(\d+)"',
    r'[Ll]ike this video along with ([\d,]+) other people',
)


def _to_int(text):
    try:
        return int(str(text).replace(",", "").strip())
    except Exception:
        return None


def youtube_video_id(url):
    """The video id from a youtube.com/shorts/, watch?v= or
    youtu.be/ URL — or None."""
    if not url:
        return None
    m = re.search(r"(?:shorts/|watch\?v=|youtu\.be/)([\w-]{6,})",
                  str(url))
    return m.group(1) if m else None


def _fetch(url):
    """GET a public page as text, or None on any failure."""
    try:
        import requests
        r = requests.get(url, headers=_HEADERS, timeout=25)
        if r.status_code == 200:
            return r.text
        return None
    except Exception:
        pass
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception:
        return None


def _first_count(html, patterns):
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            n = _to_int(m.group(1))
            if n is not None:
                return n
    return None


def youtube_stats(url):
    """Public view/like counts for one YouTube URL.

    Returns {"views": int|None, "likes": int|None} — None means
    'not publicly readable right now', never a guess. Tries the
    entry's own URL first (a Shorts URL answers where the watch
    URL may be rate-limited), then the canonical watch and Shorts
    forms of the same video.
    """
    vid = youtube_video_id(url)
    if not vid:
        return {"views": None, "likes": None}
    candidates = [url,
                  f"https://www.youtube.com/shorts/{vid}",
                  f"https://www.youtube.com/watch?v={vid}"]
    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        html = _fetch(candidate)
        if not html:
            continue
        views = _first_count(html, _VIEW_PATTERNS)
        if views is None:
            continue
        return {"views": views,
                "likes": _first_count(html, _LIKE_PATTERNS)}
    return {"views": None, "likes": None}


def _find_url(obj):
    """First http(s) URL string anywhere inside a queue field."""
    if isinstance(obj, str):
        return obj if obj.startswith("http") else None
    if isinstance(obj, dict):
        for v in obj.values():
            u = _find_url(v)
            if u:
                return u
    if isinstance(obj, (list, tuple)):
        for v in obj:
            u = _find_url(v)
            if u:
                return u
    return None


def entry_url(entry):
    """The public URL an entry was published to, or None."""
    url = entry.get("published_url")
    if url:
        return str(url)
    return _find_url(entry.get("results"))


def published_entries(queue_path=None):
    """Queue entries that are actually out in the world: status
    published/partial, or carrying a published URL."""
    out = []
    for e in ApprovalQueue(queue_path).all():
        if e.get("status") in ("published", "partial") or \
                entry_url(e):
            out.append(e)
    return out


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def snapshot(queue_path=None, out_path=None, today=None):
    """One analytics snapshot: fetch fresh public stats for every
    published entry, append one row per entry to the analytics
    log, and return the rows plus totals/top performer. A failed
    fetch degrades that entry to nulls — the run never fails and
    never fabricates."""
    out_path = out_path or ANALYTICS_PATH
    today = today or date.today()
    rows = []
    for entry in published_entries(queue_path):
        url = entry_url(entry)
        platform = str(entry.get("platform") or "").strip()
        if not platform:
            platform = ("youtube" if url and "youtu" in url
                        else "unknown")
        views = likes = None
        if platform == "youtube" and url:
            stats = youtube_stats(url)
            views, likes = stats["views"], stats["likes"]
        pub = _parse_date(entry.get("published_at"))
        days_live = (today - pub).days if pub else None
        if days_live is not None and days_live < 0:
            days_live = 0
        views_per_day = None
        if views is not None and days_live is not None:
            views_per_day = round(views / max(days_live, 1), 1)
        rows.append({
            "time": datetime.now().isoformat(),
            "entry_id": entry.get("id"),
            "platform": platform,
            "url": url,
            "published_at": entry.get("published_at"),
            "days_live": days_live,
            "views": views,
            "likes": likes,
            "views_per_day": views_per_day,
        })
    if rows:
        try:
            with open(out_path, "a", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            pass
    counted = [r for r in rows if r["views"] is not None]
    top = max(counted, key=lambda r: r["views"], default=None)
    return {
        "ok": True,
        "count": len(rows),
        "rows": rows,
        "total_views": sum(r["views"] for r in counted),
        "total_likes": sum(r["likes"] for r in rows
                           if r["likes"] is not None),
        "top": ({"entry_id": top["entry_id"], "url": top["url"],
                 "views": top["views"],
                 "views_per_day": top["views_per_day"]}
                if top else None),
    }


def print_summary(result):
    print(f"📊 analytics_robot: snapshot of {result['count']} "
          f"published entr{'y' if result['count'] == 1 else 'ies'}")
    for r in result["rows"]:
        views = r["views"] if r["views"] is not None else "—"
        likes = r["likes"] if r["likes"] is not None else "—"
        vpd = (r["views_per_day"]
               if r["views_per_day"] is not None else "—")
        print(f"  • {r['entry_id']} [{r['platform']}] "
              f"views={views} likes={likes} views/day={vpd} "
              f"days_live={r['days_live']} — {r['url']}")
    if result["top"]:
        t = result["top"]
        print(f"🏆 top performer: {t['entry_id']} — {t['views']} "
              f"views ({t['views_per_day']}/day)")
    print(f"Totals: {result['total_views']} views, "
          f"{result['total_likes']} likes "
          f"(public counts only; unreadable counts stay empty)")


def main(argv):
    queue_path, out_path = None, None
    args = list(argv[1:])
    while args:
        a = args.pop(0)
        if a == "--queue":
            queue_path = args.pop(0)
        elif a == "--out":
            out_path = args.pop(0)
    result = snapshot(queue_path=queue_path, out_path=out_path)
    print_summary(result)
    return 0


ANALYTICS_ROBOT = {"snapshot": snapshot,
                   "published_entries": published_entries,
                   "youtube_stats": youtube_stats}

if __name__ == "__main__":
    sys.exit(main(sys.argv))
