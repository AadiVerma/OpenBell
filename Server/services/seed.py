"""Seed the watchlist from NSE index CSV files.

NSE publishes constituent CSVs at nsearchives.nseindia.com — no auth needed,
but a browser-like User-Agent is required to avoid 403s.
"""
import csv
import io
import logging

import httpx

logger = logging.getLogger(__name__)

# ── NSE archive CSV URLs ──────────────────────────────────────────────────────
INDEX_URLS = {
    "NIFTY50":      "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "NIFTYNEXT50":  "https://nsearchives.nseindia.com/content/indices/ind_niftynext50list.csv",
    "NIFTY100":     "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv",
    "NIFTY200":     "https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv",
    "NIFTY500":     "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "NIFTYIT":      "https://nsearchives.nseindia.com/content/indices/ind_niftyitlist.csv",
    "NIFTYBANK":    "https://nsearchives.nseindia.com/content/indices/ind_niftybanklist.csv",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

# ── Hardcoded NIFTY 50 fallback (current as of Apr 2025) ─────────────────────
NIFTY50_FALLBACK = [
    ("ADANIENT",    "Adani Enterprises"),
    ("ADANIPORTS",  "Adani Ports & SEZ"),
    ("APOLLOHOSP",  "Apollo Hospitals"),
    ("ASIANPAINT",  "Asian Paints"),
    ("AXISBANK",    "Axis Bank"),
    ("BAJAJ-AUTO",  "Bajaj Auto"),
    ("BAJFINANCE",  "Bajaj Finance"),
    ("BAJAJFINSV",  "Bajaj Finserv"),
    ("BPCL",        "Bharat Petroleum"),
    ("BHARTIARTL",  "Bharti Airtel"),
    ("BRITANNIA",   "Britannia Industries"),
    ("CIPLA",       "Cipla"),
    ("COALINDIA",   "Coal India"),
    ("DIVISLAB",    "Divi's Laboratories"),
    ("DRREDDY",     "Dr. Reddy's Laboratories"),
    ("EICHERMOT",   "Eicher Motors"),
    ("GRASIM",      "Grasim Industries"),
    ("HCLTECH",     "HCL Technologies"),
    ("HDFCBANK",    "HDFC Bank"),
    ("HDFCLIFE",    "HDFC Life Insurance"),
    ("HEROMOTOCO",  "Hero MotoCorp"),
    ("HINDALCO",    "Hindalco Industries"),
    ("HINDUNILVR",  "Hindustan Unilever"),
    ("ICICIBANK",   "ICICI Bank"),
    ("ITC",         "ITC"),
    ("INDUSINDBK",  "IndusInd Bank"),
    ("INFY",        "Infosys"),
    ("JSWSTEEL",    "JSW Steel"),
    ("KOTAKBANK",   "Kotak Mahindra Bank"),
    ("LT",          "Larsen & Toubro"),
    ("LTIM",        "LTIMindtree"),
    ("M&M",         "Mahindra & Mahindra"),
    ("MARUTI",      "Maruti Suzuki India"),
    ("NESTLEIND",   "Nestle India"),
    ("NTPC",        "NTPC"),
    ("ONGC",        "Oil & Natural Gas Corp"),
    ("POWERGRID",   "Power Grid Corp"),
    ("RELIANCE",    "Reliance Industries"),
    ("SBILIFE",     "SBI Life Insurance"),
    ("SHRIRAMFIN",  "Shriram Finance"),
    ("SBIN",        "State Bank of India"),
    ("SUNPHARMA",   "Sun Pharmaceutical"),
    ("TCS",         "Tata Consultancy Services"),
    ("TATACONSUM",  "Tata Consumer Products"),
    ("TATAMOTORS",  "Tata Motors"),
    ("TATASTEEL",   "Tata Steel"),
    ("TECHM",       "Tech Mahindra"),
    ("TITAN",       "Titan Company"),
    ("ULTRACEMCO",  "UltraTech Cement"),
    ("WIPRO",       "Wipro"),
]


async def fetch_nse_index(index_key: str) -> list[dict]:
    """
    Fetch NSE index constituent CSV and return list of
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries", "exchange": "NSE"}.

    Falls back to hardcoded NIFTY 50 list on any error.
    """
    url = INDEX_URLS.get(index_key.upper())
    if not url:
        raise ValueError(f"Unknown index '{index_key}'. Options: {list(INDEX_URLS)}")

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=_HEADERS)
            resp.raise_for_status()

        text = resp.text
        reader = csv.DictReader(io.StringIO(text))
        stocks = []
        for row in reader:
            symbol = (row.get("Symbol") or row.get("symbol") or "").strip()
            name   = (row.get("Company Name") or row.get("company name") or symbol).strip()
            if symbol:
                stocks.append({
                    "ticker":   f"{symbol}.NS",
                    "name":     name,
                    "exchange": "NSE",
                })

        logger.info("Fetched %d stocks from NSE %s CSV", len(stocks), index_key)
        return stocks

    except Exception as exc:
        logger.warning("NSE CSV fetch failed (%s) — using hardcoded fallback: %s", index_key, exc)
        if index_key.upper() == "NIFTY50":
            return [
                {"ticker": f"{sym}.NS", "name": name, "exchange": "NSE"}
                for sym, name in NIFTY50_FALLBACK
            ]
        raise RuntimeError(
            f"Could not fetch {index_key} from NSE and no fallback available. "
            "Try NIFTY50 or check your internet connection."
        ) from exc
