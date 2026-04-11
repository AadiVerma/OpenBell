"""
NSE index seeder — fetches ticker lists from NSE archives.
Falls back to hardcoded lists if the network request fails.

Returns a list of {ticker, name} dicts with .NS suffix already appended.
"""
from __future__ import annotations

import csv
import io
import logging
import urllib.request

logger = logging.getLogger(__name__)

_NSE_CSV_URLS: dict[str, str] = {
    "NIFTY50": "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "NIFTYNEXT50": "https://nsearchives.nseindia.com/content/indices/ind_niftynext50list.csv",
    "NIFTY100": "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv",
    "NIFTY200": "https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv",
    "NIFTY500": "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "NIFTYIT": "https://nsearchives.nseindia.com/content/indices/ind_niftyitlist.csv",
    "NIFTYBANK": "https://nsearchives.nseindia.com/content/indices/ind_niftybanklist.csv",
    "NIFTYREIT": "https://nsearchives.nseindia.com/content/indices/ind_niftyreitsinfraivlist.csv",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Fallback hardcoded lists ──────────────────────────────────────────────────

_NIFTY50_FALLBACK = [
    ("RELIANCE", "Reliance Industries"), ("TCS", "Tata Consultancy Services"),
    ("HDFCBANK", "HDFC Bank"), ("ICICIBANK", "ICICI Bank"), ("INFY", "Infosys"),
    ("HINDUNILVR", "Hindustan Unilever"), ("ITC", "ITC"), ("SBIN", "State Bank of India"),
    ("BHARTIARTL", "Bharti Airtel"), ("KOTAKBANK", "Kotak Mahindra Bank"),
    ("LT", "Larsen & Toubro"), ("AXISBANK", "Axis Bank"), ("ASIANPAINT", "Asian Paints"),
    ("MARUTI", "Maruti Suzuki"), ("TITAN", "Titan Company"),
    ("BAJFINANCE", "Bajaj Finance"), ("WIPRO", "Wipro"),
    ("ULTRACEMCO", "UltraTech Cement"), ("NESTLEIND", "Nestle India"),
    ("SUNPHARMA", "Sun Pharmaceutical"), ("POWERGRID", "Power Grid Corp"),
    ("ONGC", "Oil and Natural Gas"), ("NTPC", "NTPC"), ("JSWSTEEL", "JSW Steel"),
    ("TATAMOTORS", "Tata Motors"), ("M&M", "Mahindra & Mahindra"),
    ("HCLTECH", "HCL Technologies"), ("ADANIENT", "Adani Enterprises"),
    ("ADANIPORTS", "Adani Ports"), ("COALINDIA", "Coal India"),
    ("BAJAJFINSV", "Bajaj Finserv"), ("DRREDDY", "Dr. Reddy's Laboratories"),
    ("GRASIM", "Grasim Industries"), ("TECHM", "Tech Mahindra"),
    ("DIVISLAB", "Divi's Laboratories"), ("CIPLA", "Cipla"),
    ("EICHERMOT", "Eicher Motors"), ("BPCL", "Bharat Petroleum"),
    ("TATACONSUM", "Tata Consumer Products"), ("HEROMOTOCO", "Hero MotoCorp"),
    ("SHREECEM", "Shree Cement"), ("APOLLOHOSP", "Apollo Hospitals"),
    ("INDUSINDBK", "IndusInd Bank"), ("BRITANNIA", "Britannia Industries"),
    ("HINDALCO", "Hindalco Industries"), ("TATASTEEL", "Tata Steel"),
    ("SBILIFE", "SBI Life Insurance"), ("HDFCLIFE", "HDFC Life Insurance"),
    ("UPL", "UPL"), ("BAJAJ-AUTO", "Bajaj Auto"),
]

_NIFTYREIT_FALLBACK = [
    ("EMBASSY", "Embassy Office Parks REIT"),
    ("MINDSPACE", "Mindspace Business Parks REIT"),
    ("BROOKFIELD", "Brookfield India Real Estate Trust"),
    ("NEXUS", "Nexus Select Trust"),
    ("NXST", "Navi Mumbai Special Economic Zone"),
    ("LODHA", "Lodha Group"),
    ("PRESTIGE", "Prestige Estates Projects"),
]

_FALLBACKS: dict[str, list[tuple[str, str]]] = {
    "NIFTY50": _NIFTY50_FALLBACK,
    "NIFTYREIT": _NIFTYREIT_FALLBACK,
}


def fetch_index_tickers(index: str) -> list[dict]:
    """
    Return list of {ticker, name} for the given NSE index name.
    Tries live NSE CSV first; falls back to hardcoded list.
    """
    index = index.upper()
    url = _NSE_CSV_URLS.get(index)
    if url:
        tickers = _fetch_from_nse(url)
        if tickers:
            return tickers

    # Use fallback if available
    fallback = _FALLBACKS.get(index, [])
    if fallback:
        logger.warning("Using hardcoded fallback list for %s (%d stocks)", index, len(fallback))
        return [{"ticker": f"{sym}.NS", "name": name} for sym, name in fallback]

    logger.error("No tickers found for index %s", index)
    return []


def _fetch_from_nse(url: str) -> list[dict]:
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        reader = csv.DictReader(io.StringIO(raw))
        tickers = []
        for row in reader:
            symbol = (row.get("Symbol") or "").strip()
            name = (row.get("Company Name") or row.get("Name") or symbol).strip()
            if symbol:
                tickers.append({"ticker": f"{symbol}.NS", "name": name})
        return tickers

    except Exception as exc:
        logger.warning("NSE CSV fetch failed (%s): %s", url, exc)
        return []
