"""
High-level entry point for AI-powered stock analysis.

Automatically selects the right path based on config:

  SDK path  (ANTHROPIC_API_KEY is set)
    → Uses the Anthropic Python SDK with forced tool_use.
    → Most token-efficient. Recommended for production.

  CLI path  (no API key — uses the `claude` terminal CLI)
    → Calls `claude -p prompt` as a subprocess.
    → Works with Claude Code subscription, no separate API key needed.
    → Same compressed data format; schema is embedded in the prompt.

Call analyze_stock() from services — never instantiate clients elsewhere.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StockPrediction:
    signal: str
    confidence: int
    predicted_direction: str
    target_low: float
    target_high: float
    limit_price: float
    reasoning: str
    factors: list[dict]


async def analyze_stock(
    ticker: str,
    market_data: dict,
    news: list[dict],
) -> StockPrediction:
    from app.core.config import get_settings
    settings = get_settings()

    if settings.ANTHROPIC_API_KEY:
        return await _analyze_sdk(ticker, market_data, news, settings)
    else:
        return await _analyze_cli(ticker, market_data, news)


# ── SDK path ──────────────────────────────────────────────────────────────────

async def _analyze_sdk(ticker: str, market_data: dict, news: list[dict], settings) -> StockPrediction:
    from app.ai.client import get_client
    from app.ai.prompts import SYSTEM_PROMPT, build_user_message
    from app.ai.tools import PREDICTION_TOOL

    client = get_client()
    user_msg = build_user_message(ticker, market_data, news)

    response = await client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[PREDICTION_TOOL],
        tool_choice={"type": "tool", "name": "submit_prediction"},
        messages=[{"role": "user", "content": user_msg}],
    )

    logger.debug(
        "SDK analyze(%s) tokens: input=%d output=%d",
        ticker,
        response.usage.input_tokens,
        response.usage.output_tokens,
    )

    tool_block = next(b for b in response.content if b.type == "tool_use")
    return _parse_prediction(tool_block.input)


# ── CLI path ──────────────────────────────────────────────────────────────────

async def _analyze_cli(ticker: str, market_data: dict, news: list[dict]) -> StockPrediction:
    from app.ai.prompts import build_cli_prompt

    prompt = build_cli_prompt(ticker, market_data, news)
    logger.debug("CLI analyze(%s) prompt_len=%d chars", ticker, len(prompt))

    # yfinance already blocks; run claude CLI in thread pool too
    raw_text = await asyncio.to_thread(_run_claude_cli, prompt)
    data = _extract_json(raw_text)
    return _parse_prediction(data)


def _run_claude_cli(prompt: str) -> str:
    """Synchronous subprocess call to the `claude` CLI."""
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr[:300]}")

    cli_data = json.loads(result.stdout)
    if cli_data.get("is_error"):
        raise RuntimeError(f"Claude CLI error: {cli_data}")

    return cli_data["result"]


def _extract_json(text: str) -> dict:
    """Extract a JSON object from CLI response, tolerating markdown fences."""
    # Try ```json ... ``` block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)

    # Find outermost braces
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        return json.loads(stripped[start: end + 1])

    raise ValueError(f"No JSON found in CLI response:\n{text[:400]}")


# ── Shared ────────────────────────────────────────────────────────────────────

def _parse_prediction(data: dict) -> StockPrediction:
    return StockPrediction(
        signal=data["signal"],
        confidence=int(data["confidence"]),
        predicted_direction=data["predicted_direction"],
        target_low=float(data["target_low"]),
        target_high=float(data["target_high"]),
        limit_price=float(data["limit_price"]),
        reasoning=data["reasoning"],
        factors=data["factors"],
    )
