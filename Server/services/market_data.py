import asyncio
import logging
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def _fetch(ticker: str) -> Optional[dict]:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="30d", auto_adjust=False)

        if hist.empty:
            return None

        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest

        # fast_info.last_price hits a lighter endpoint and is more reliable
        # for Indian REITs/InvITs where info["currentPrice"] is often stale
        try:
            current_price = float(stock.fast_info.last_price)
        except Exception:
            current_price = float(
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or latest["Close"]
            )
        prev_close = float(
            info.get("regularMarketPreviousClose") or prev["Close"]
        )
        change_pct = ((current_price - prev_close) / prev_close) * 100

        # RSI-14
        closes = hist["Close"]
        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi = None if pd.isna(rsi_series.iloc[-1]) else round(float(rsi_series.iloc[-1]), 1)

        return {
            "ticker": ticker,
            "name": info.get("longName", ticker),
            "current_price": current_price,
            "prev_close": prev_close,
            "change_pct": round(change_pct, 2),
            "volume": int(latest["Volume"]),
            "high_52w": info.get("fiftyTwoWeekHigh"),
            "low_52w": info.get("fiftyTwoWeekLow"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "rsi": rsi,
            "sector": info.get("sector"),
        }
    except Exception as e:
        logger.error("Failed to fetch market data for %s: %s", ticker, e)
        return None


async def get_stock_data(ticker: str) -> Optional[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch, ticker)
