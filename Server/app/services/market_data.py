"""
Market data fetching via yfinance.

Returns a normalised dict or None on failure — callers must handle None.
Run via asyncio.to_thread() since yfinance is synchronous.
"""
from __future__ import annotations

import logging

import yfinance as yf

logger = logging.getLogger(__name__)

_HISTORY_PERIOD = "30d"
_RSI_PERIOD = 14


def _compute_rsi(closes: list[float], period: int = _RSI_PERIOD) -> float | None:
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-period:]
    avg_gain = sum(max(d, 0) for d in recent) / period
    avg_loss = sum(abs(min(d, 0)) for d in recent) / period
    if avg_loss == 0:
        return 100.0
    return round(100 - 100 / (1 + avg_gain / avg_loss), 2)


def fetch_market_data(ticker: str) -> dict | None:
    """
    Fetch 30-day OHLCV history + fundamentals for a ticker.
    Returns a compact dict suitable for the AI prompt builder.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=_HISTORY_PERIOD)

        if hist.empty:
            logger.warning("No history data for %s", ticker)
            return None

        closes = hist["Close"].tolist()
        volumes = hist["Volume"].tolist()

        current_price = closes[-1]
        prev_close = closes[-2] if len(closes) > 1 else current_price
        change_pct = round((current_price - prev_close) / prev_close * 100, 2)

        avg_vol = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
        volume_ratio = round(volumes[-1] / avg_vol, 2) if avg_vol else 1.0

        info: dict = {}
        try:
            info = stock.info or {}
        except Exception:
            pass

        # Prefer info fields; fall back to computed values from history
        week_52_high = info.get("fiftyTwoWeekHigh") or max(closes)
        week_52_low = info.get("fiftyTwoWeekLow") or min(closes)

        return {
            "current_price": round(current_price, 2),
            "prev_close": round(prev_close, 2),
            "change_pct": change_pct,
            "volume": int(volumes[-1]),
            "volume_ratio": volume_ratio,
            "rsi": _compute_rsi(closes),
            "week_52_high": round(week_52_high, 2),
            "week_52_low": round(week_52_low, 2),
            "pe_ratio": info.get("trailingPE"),
            "sector": info.get("sector") or info.get("industry") or "",
        }

    except Exception as exc:
        logger.error("Market data fetch failed for %s: %s", ticker, exc)
        return None
