"""
WhatsApp text report builder.
Splits output into chunks of ≤1500 chars suitable for Twilio messages.
"""
from __future__ import annotations

import math
from datetime import date

from app.core.config import Settings
from app.models.prediction import Prediction

_CHUNK_LIMIT = 1500


def _position_alloc(confidence: int, budget: float) -> float:
    """Return capital to allocate based on confidence tier."""
    if confidence >= 80:
        pct = 0.15
    elif confidence >= 70:
        pct = 0.10
    elif confidence >= 60:
        pct = 0.07
    else:
        pct = 0.05
    return round(budget * pct, 2)


def build_report(predictions: list[Prediction], settings: Settings) -> list[str]:
    """Return a list of message chunks, each ≤1500 chars."""
    budget = settings.PORTFOLIO_BUDGET
    today = date.today().strftime("%d %b %Y")

    bullish = sorted(
        [p for p in predictions if p.signal == "bullish" and p.confidence >= 60],
        key=lambda p: p.confidence,
        reverse=True,
    )
    bearish = sorted(
        [p for p in predictions if p.signal == "bearish" and p.confidence >= 60],
        key=lambda p: p.confidence,
        reverse=True,
    )

    lines: list[str] = [
        f"📊 *OpenBell Signals — {today}*",
        f"Analysed: {len(predictions)} | Buys: {len(bullish)} | Alerts: {len(bearish)}",
        "",
        "🟢 *TOP BUY SIGNALS*",
    ]

    if bullish:
        for p in bullish[:5]:
            alloc = _position_alloc(p.confidence, budget)
            qty = max(1, math.floor(alloc / p.limit_price)) if p.limit_price else 0
            stop = round(p.limit_price * 0.97, 2)
            rr = round((p.target_high - p.limit_price) / (p.limit_price - stop), 2) if (p.limit_price - stop) else "—"
            lines += [
                f"• *{p.ticker}* ({p.confidence}%) @ ₹{p.limit_price:.2f}",
                f"  Target: ₹{p.target_low:.2f}–{p.target_high:.2f} | Stop: ₹{stop} | R:R {rr} | Qty: {qty}",
            ]
    else:
        lines.append("No high-confidence buy signals today.")

    if bearish:
        lines += ["", "🔴 *BEARISH ALERTS*"]
        for p in bearish[:3]:
            lines.append(
                f"• *{p.ticker}* ({p.confidence}%) target ₹{p.target_low:.2f} — "
                f"{p.reasoning[:80]}…"
            )

    lines += ["", "_AI-generated signals. Not financial advice._"]

    # Split into chunks
    chunks: list[str] = []
    current = ""
    for line in lines:
        candidate = (current + "\n" + line) if current else line
        if len(candidate) > _CHUNK_LIMIT:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)

    return chunks
