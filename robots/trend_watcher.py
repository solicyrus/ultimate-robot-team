"""ULTIMATE ROBOT TEAM — robots/trend_watcher.py

A REAL trend-watching robot. It searches the live web with DuckDuckGo
and returns real result titles + URLs for a niche — never invented.

Technical note: DuckDuckGo's plain GET endpoint serves a bot-challenge
page on this network, but submitting the search as an HTML FORM (POST)
returns real results. That's what this robot does (stdlib only).

watch(niche, max_results=5) ->
    {"ok": True, "query": ..., "trends": [{"title","url"}, ...]}
    {"ok": False, "error": "..."} when the search genuinely fails.
"""

import html as html_module
import re
import time
import urllib.parse
import urllib.request

_DDG = "https://html.duckduckgo.com/html/"
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def _search_once(query):
    form = urllib.parse.urlencode({"q": query}).encode("utf-8")
    req = urllib.request.Request(
        _DDG, data=form,
        headers={"User-Agent": _UA,
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        page = resp.read().decode("utf-8", errors="replace")
    trends = []
    for m in re.finditer(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            page, re.DOTALL):
        href, title_html = m.group(1), m.group(2)
        if "uddg=" in href:  # unwrap DuckDuckGo's redirect wrapper
            href = urllib.parse.unquote(href.split("uddg=", 1)[1].split("&")[0])
        title = html_module.unescape(re.sub(r"<[^>]+>", "", title_html).strip())
        if href.startswith("http") and title:
            trends.append({"title": title, "url": href})
    return trends


def watch(niche, max_results=5):
    """Search the live web for what's trending in a niche.

    Never raises — returns {"ok": False, "error": ...} on real failure.
    """
    query = f"{niche} trends social media"
    last_err = None
    # The egress path to DuckDuckGo is flaky (occasional bot-challenge
    # pages); retry with backoff and report honestly if all fail.
    for attempt in range(3):
        try:
            trends = _search_once(query)
            if trends:
                return {"ok": True, "query": query,
                        "trends": trends[:max_results]}
            last_err = "no results parsed (page layout or block)"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(1 * (2 ** attempt))
    return {"ok": False, "query": query, "trends": [], "error": last_err}
