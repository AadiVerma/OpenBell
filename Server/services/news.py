"""News fetching service.

Strategy:
- Indian stocks (.NS / .BO)  → Google News RSS  (free, no key, good Indian coverage)
- US / other stocks          → Finnhub company-news API (requires FINNHUB_API_KEY)
"""

import asyncio
import logging
from datetime import date, timedelta
from urllib.parse import quote

import feedparser
import httpx

from core.config import settings

logger = logging.getLogger(__name__)
FINNHUB_BASE = "https://finnhub.io/api/v1"


# ── helpers ──────────────────────────────────────────────────────────────────

def _is_indian(ticker: str) -> bool:
    return ticker.endswith(".NS") or ticker.endswith(".BO")


def _to_finnhub_symbol(ticker: str) -> str:
    if ticker.endswith(".NS"):
        return f"NSE:{ticker[:-3]}"
    if ticker.endswith(".BO"):
        return f"BSE:{ticker[:-3]}"
    return ticker


def _clean_ticker(ticker: str) -> str:
    """Strip exchange suffix: RELIANCE.NS → RELIANCE"""
    return ticker.split(".")[0]


# ── Google News RSS (Indian stocks) ──────────────────────────────────────────

def _fetch_google_news(ticker: str, company_name: str = "") -> list[dict]:
    clean = _clean_ticker(ticker)
    query = f"{clean} {company_name} stock NSE".strip() if company_name else f"{clean} NSE stock"
    url = (
        f"https://news.google.com/rss/search"
        f"?q={quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:5]:
            articles.append({
                "title": entry.get("title", ""),
                "summary": (entry.get("summary") or "")[:300],
                "published": entry.get("published", ""),
                "source": (entry.get("source") or {}).get("title", "Google News"),
                "url": entry.get("link", ""),
            })
        return articles
    except Exception as exc:
        logger.warning("Google News RSS failed for %s: %s", ticker, exc)
        return []


async def _fetch_google_news_async(ticker: str, company_name: str = "") -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_google_news, ticker, company_name)


# ── Finnhub (US / global stocks) ─────────────────────────────────────────────

async def _fetch_finnhub_news(ticker: str) -> list[dict]:
    if not settings.FINNHUB_API_KEY:
        logger.warning("FINNHUB_API_KEY not set — skipping news for %s", ticker)
        return []

    today = date.today()
    params = {
        "symbol": _to_finnhub_symbol(ticker),
        "from": (today - timedelta(days=7)).strftime("%Y-%m-%d"),
        "to": today.strftime("%Y-%m-%d"),
        "token": settings.FINNHUB_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{FINNHUB_BASE}/company-news", params=params)
            resp.raise_for_status()
            articles = resp.json()

        if not isinstance(articles, list):
            return []

        return [
            {
                "title": a.get("headline", ""),
                "summary": (a.get("summary") or "")[:300],
                "published": a.get("datetime", ""),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
            }
            for a in articles[:5]
        ]
    except Exception as exc:
        logger.warning("Finnhub news failed for %s: %s", ticker, exc)
        return []


# ── public API ────────────────────────────────────────────────────────────────

async def get_stock_news(ticker: str, company_name: str = "") -> list[dict]:
    """Return up to 5 recent news articles for *ticker*.

    Uses Google News RSS for Indian stocks, Finnhub for everything else.
    Always returns a list (empty on failure) so predictions still run.
    """
    if _is_indian(ticker):
        articles = await _fetch_google_news_async(ticker, company_name)
        logger.info("Google News: %d articles for %s", len(articles), ticker)
    else:
        articles = await _fetch_finnhub_news(ticker)
        logger.info("Finnhub: %d articles for %s", len(articles), ticker)

    return articles
