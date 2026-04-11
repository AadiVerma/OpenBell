"""
News fetching with two strategies:

  Indian stocks (.NS / .BO)  → Google News RSS (free, no key)
  Global stocks              → Finnhub REST API (requires FINNHUB_API_KEY)
                               falls back to Google News if no key configured

Returns a normalised list of dicts: {title, url, published_at, age_label}
Always returns a list (empty on failure) — predictions must still run without news.

Run via asyncio.to_thread() since all I/O here is synchronous.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import feedparser

logger = logging.getLogger(__name__)
_MAX_ARTICLES = 5


def _age_label(published_str: str) -> str:
    """Convert a date string to a human-readable age label like '2h' or '3d'."""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(published_str)
        delta = datetime.now(timezone.utc) - dt
        hours = int(delta.total_seconds() // 3600)
        if hours < 24:
            return f"{hours}h"
        return f"{hours // 24}d"
    except Exception:
        return ""


def _google_news(query: str) -> list[dict]:
    encoded = urllib.parse.quote(query)
    url = (
        f"https://news.google.com/rss/search"
        f"?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:_MAX_ARTICLES]:
            articles.append(
                {
                    "title": entry.get("title", "").strip(),
                    "url": entry.get("link", ""),
                    "published_at": entry.get("published", ""),
                    "age_label": _age_label(entry.get("published", "")),
                }
            )
        return articles
    except Exception as exc:
        logger.warning("Google News fetch failed for '%s': %s", query, exc)
        return []


def _finnhub_news(ticker: str) -> list[dict]:
    from app.core.config import get_settings
    api_key = get_settings().FINNHUB_API_KEY
    if not api_key:
        return []

    now = int(time.time())
    week_ago = now - 7 * 86400
    date_from = datetime.fromtimestamp(week_ago, tz=timezone.utc).strftime("%Y-%m-%d")
    date_to = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")
    url = (
        f"https://finnhub.io/api/v1/company-news"
        f"?symbol={ticker}&from={date_from}&to={date_to}&token={api_key}"
    )
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            articles = json.loads(resp.read())[:_MAX_ARTICLES]
        return [
            {
                "title": a.get("headline", "").strip(),
                "url": a.get("url", ""),
                "published_at": datetime.fromtimestamp(
                    a.get("datetime", 0), tz=timezone.utc
                ).isoformat(),
                "age_label": _age_label(
                    datetime.fromtimestamp(
                        a.get("datetime", 0), tz=timezone.utc
                    ).strftime("%a, %d %b %Y %H:%M:%S %z")
                ),
            }
            for a in articles
        ]
    except Exception as exc:
        logger.warning("Finnhub news fetch failed for '%s': %s", ticker, exc)
        return []


def fetch_news(ticker: str) -> list[dict]:
    """Return up to 5 normalised news articles for the given ticker."""
    if ticker.endswith((".NS", ".BO")):
        clean = ticker.rsplit(".", 1)[0]
        return _google_news(f"{clean} NSE stock")

    # Global: try Finnhub first, fall back to Google
    return _finnhub_news(ticker) or _google_news(ticker)
