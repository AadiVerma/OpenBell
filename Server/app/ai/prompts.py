"""
Prompt builders for stock prediction.

Two modes:
  SDK mode  (ANTHROPIC_API_KEY set) — schema lives in tools.py via tool_use.
                                       Data block only, no schema in prompt.
  CLI mode  (no API key, uses `claude` CLI) — schema embedded in prompt.
                                       Still uses compressed data format.

Token savings vs original in both modes:
  - Compressed market data: ~100 tokens vs ~400 tokens (original verbose format)
  - SDK: schema NOT repeated in prompt (tool_use handles it)
  - CLI: schema included once but written compactly (~80 tokens vs ~250 original)

To improve prediction quality later:
  - Add sector-relative PE, moving average crossovers, FII/DII flow data
"""
from __future__ import annotations

# ── SDK mode system prompt (schema is in tools.py, not here) ─────────────────

SYSTEM_PROMPT = """\
You are a quantitative equity analyst specialising in Indian and global stock markets.
Analyse the stock data provided and generate a next-day trading signal using the submit_prediction tool.

Analysis guidelines:
- Default to neutral when signals are mixed or data quality is low.
- RSI > 70 → overbought caution; RSI < 30 → oversold opportunity.
- Price near 52W high → resistance; near 52W low → support or distribution.
- Volume spike (>1.5x avg) confirms price moves; low volume weakens them.
- Confidence reflects data clarity, not profit certainty.
- Target range should be realistic for a single trading day.
- Limit price: bullish → 1-2% below current (widen to 2-3% if confidence < 60);
  bearish/neutral → at or just above current."""

# ── CLI mode prompt (schema embedded — used when no API key) ──────────────────

_CLI_SCHEMA = """\
Reply with ONLY a JSON object, no markdown fences:
{"signal":"bullish"|"bearish"|"neutral","confidence":0-100,"predicted_direction":"up"|"down"|"neutral",\
"target_low":number,"target_high":number,"limit_price":number,"reasoning":"3-5 sentences",\
"factors":[{"type":"bullish"|"bearish"|"risk","text":"one line"},... 3-5 items]}"""

CLI_SYSTEM_PROMPT = """\
You are a quantitative equity analyst. Analyse the stock data and predict tomorrow's price movement.
- Default neutral when signals are mixed.
- RSI >70 overbought, <30 oversold. Volume >1.5x confirms moves.
- Limit: bullish → 1-2% below current (2-3% if confidence<60); bearish/neutral → at current."""


def build_user_message(ticker: str, market_data: dict, news: list[dict]) -> str:
    """
    Compress stock data into a minimal prompt block.
    Only include fields that meaningfully affect the prediction.
    """
    price = market_data.get("current_price", 0.0)
    change = market_data.get("change_pct", 0.0)
    vol_ratio = market_data.get("volume_ratio", 1.0)
    rsi = market_data.get("rsi")
    w52_low = market_data.get("week_52_low", price * 0.8)
    w52_high = market_data.get("week_52_high", price * 1.2)
    pe = market_data.get("pe_ratio")
    sector = market_data.get("sector", "")

    # 52-week position as a percentile (0% = at low, 100% = at high)
    w52_pos = (
        round((price - w52_low) / (w52_high - w52_low) * 100)
        if w52_high != w52_low
        else 50
    )

    lines = [
        f"TICKER: {ticker}",
        f"PRICE: {price:.2f} ({change:+.2f}%)",
        f"VOL: {vol_ratio:.1f}x avg | RSI14: {rsi:.1f}" if rsi else f"VOL: {vol_ratio:.1f}x avg",
        f"52W: {w52_low:.2f}/{w52_high:.2f} (pos: {w52_pos}%)",
    ]

    if pe:
        lines.append(f"PE: {pe:.1f}" + (f" | SECTOR: {sector}" if sector else ""))
    elif sector:
        lines.append(f"SECTOR: {sector}")

    if news:
        lines.append("NEWS:")
        for i, article in enumerate(news[:5], 1):
            title = (article.get("title") or "")[:90].strip()
            age = article.get("age_label", "")
            suffix = f" [{age}]" if age else ""
            lines.append(f"{i}. {title}{suffix}")
    else:
        lines.append("NEWS: none")

    return "\n".join(lines)


def build_cli_prompt(ticker: str, market_data: dict, news: list[dict]) -> str:
    """
    Full prompt for the `claude` CLI subprocess path (no API key).
    Includes the JSON schema inline since tool_use is not available via CLI.
    Still uses the same compressed data format for token efficiency.
    """
    data_block = build_user_message(ticker, market_data, news)
    return f"{CLI_SYSTEM_PROMPT}\n\n{data_block}\n\n{_CLI_SCHEMA}"
