import asyncio
import json
import logging
import re
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Inline schema description embedded in the prompt — tells Claude exactly what JSON to return
_JSON_SPEC = """\
Return ONLY a JSON object (no markdown fences, no explanation) with exactly these fields:
{
  "signal":               "bullish" | "bearish" | "neutral",
  "confidence":           integer 0-100,
  "predicted_direction":  "up" | "down" | "neutral",
  "target_low":           number  (lower bound of expected price range tomorrow),
  "target_high":          number  (upper bound of expected price range tomorrow),
  "reasoning":            string  (3-5 sentences in plain English),
  "factors": [
    {"type": "bullish" | "bearish" | "risk", "text": "one-line description"},
    ... (3-5 items)
  ],
  "limit_price":          number  (suggested buy entry, 1-3 % below current_price;
                                   use wider discount when confidence < 60)
}"""


@dataclass
class StockPrediction:
    ticker: str
    signal: str
    confidence: int
    predicted_direction: str
    target_low: float
    target_high: float
    reasoning: str
    factors: list[dict]
    limit_price: float


def _build_prompt(ticker: str, market_data: dict, news: list[dict]) -> str:
    news_lines = (
        "\n".join(f"  - {a['title']} [{a.get('source', '')}]" for a in news)
        if news
        else "  No recent news available."
    )

    return f"""You are a quantitative equity analyst. Analyse the data below and predict
tomorrow's price movement for {ticker}.

MARKET DATA
  Ticker        : {ticker}
  Name          : {market_data.get('name', ticker)}
  Current Price : {market_data['current_price']}
  Prev Close    : {market_data['prev_close']}
  Today Change  : {market_data['change_pct']}%
  RSI (14)      : {market_data.get('rsi', 'N/A')}
  52W High      : {market_data.get('high_52w', 'N/A')}
  52W Low       : {market_data.get('low_52w', 'N/A')}
  Volume        : {market_data.get('volume', 'N/A')}
  P/E Ratio     : {market_data.get('pe_ratio', 'N/A')}
  Sector        : {market_data.get('sector', 'N/A')}

RECENT NEWS (last 5 articles)
{news_lines}

Instructions:
- Be realistic. A "neutral" signal with moderate confidence is often more honest
  than a high-confidence directional call on noisy data.
- List 3-5 factors; tag each as bullish, bearish, or risk.

{_JSON_SPEC}"""


def _extract_json(text: str) -> dict:
    """Extract a JSON object from LLM output, tolerating markdown code fences."""
    # Try ```json ... ``` or ``` ... ``` blocks first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # Try the whole text stripped
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)

    # Find outermost braces
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        return json.loads(stripped[start : end + 1])

    raise ValueError(f"No JSON object found in Claude response:\n{text[:400]}")


def _run_claude(prompt: str) -> str:
    """Synchronous subprocess call to the Claude Code CLI."""
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True,
        text=True,
        timeout=180,    # thinking takes time
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr[:300]}")

    cli_data = json.loads(result.stdout)
    if cli_data.get("is_error"):
        raise RuntimeError(f"Claude returned an error: {cli_data}")

    return cli_data["result"]


async def predict_stock(
    ticker: str, market_data: dict, news: list[dict]
) -> StockPrediction:
    prompt = _build_prompt(ticker, market_data, news)

    loop = asyncio.get_running_loop()
    response_text = await loop.run_in_executor(None, _run_claude, prompt)

    logger.debug("Claude raw response for %s:\n%s", ticker, response_text[:500])
    data = _extract_json(response_text)

    return StockPrediction(
        ticker=ticker,
        signal=data["signal"],
        confidence=int(data["confidence"]),
        predicted_direction=data["predicted_direction"],
        target_low=float(data["target_low"]),
        target_high=float(data["target_high"]),
        reasoning=data["reasoning"],
        factors=data["factors"],
        limit_price=float(data["limit_price"]),
    )
