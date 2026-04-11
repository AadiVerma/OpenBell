"""
Background analysis orchestrator.

Runs as a FastAPI BackgroundTask inside the existing event loop — no daemon
threads, no isolated event loops, no greenlet hacks.

Usage:
    background_tasks.add_task(run_analysis, force=False)

State is held in a module-level dataclass; poll get_job_state() for progress.
An asyncio.Lock prevents concurrent runs.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.ai.analyzer import analyze_stock
from app.core.database import SessionLocal
from app.repositories.prediction import PredictionRepository
from app.repositories.watchlist import WatchlistRepository
from app.services.market_data import fetch_market_data
from app.services.news import fetch_news

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()


@dataclass
class _JobState:
    running: bool = False
    total: int = 0
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    current: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_details: list[str] = field(default_factory=list)


_state = _JobState()


def get_job_state() -> dict:
    return {
        "running": _state.running,
        "total": _state.total,
        "processed": _state.processed,
        "skipped": _state.skipped,
        "errors": _state.errors,
        "current": _state.current,
        "started_at": _state.started_at.isoformat() if _state.started_at else None,
        "finished_at": _state.finished_at.isoformat() if _state.finished_at else None,
        "error_details": _state.error_details[-10:],  # last 10 only
    }


async def run_analysis(force: bool = False) -> None:
    """Entry point for BackgroundTasks. Skips silently if already running."""
    global _state

    if _lock.locked():
        logger.info("Analysis already running — new request ignored")
        return

    async with _lock:
        _state = _JobState(running=True, started_at=datetime.now(timezone.utc))
        try:
            await _execute(force)
        except Exception as exc:
            logger.exception("Analysis job crashed: %s", exc)
        finally:
            _state.running = False
            _state.finished_at = datetime.now(timezone.utc)
            _state.current = None


async def _execute(force: bool) -> None:
    async with SessionLocal() as db:
        watchlist_repo = WatchlistRepository(db)
        pred_repo = PredictionRepository(db)

        stocks = await watchlist_repo.get_all()
        _state.total = len(stocks)
        today = datetime.now(timezone.utc).date()

        for stock in stocks:
            _state.current = stock.ticker
            try:
                if not force:
                    existing = await pred_repo.get_today(stock.ticker, today)
                    if existing:
                        _state.skipped += 1
                        continue

                # yfinance and news fetching are synchronous — offload to thread pool
                market_data = await asyncio.to_thread(fetch_market_data, stock.ticker)
                if not market_data:
                    _state.errors += 1
                    _state.error_details.append(f"{stock.ticker}: no market data")
                    continue

                news = await asyncio.to_thread(fetch_news, stock.ticker)
                prediction = await analyze_stock(stock.ticker, market_data, news)

                await pred_repo.create(
                    ticker=stock.ticker,
                    date=today,
                    signal=prediction.signal,
                    confidence=prediction.confidence,
                    predicted_direction=prediction.predicted_direction,
                    target_low=prediction.target_low,
                    target_high=prediction.target_high,
                    limit_price=prediction.limit_price,
                    reasoning=prediction.reasoning,
                    factors=prediction.factors,
                    current_price=market_data["current_price"],
                )
                _state.processed += 1
                logger.info(
                    "✓ %s → %s (%d%%)", stock.ticker, prediction.signal, prediction.confidence
                )

            except Exception as exc:
                _state.errors += 1
                _state.error_details.append(f"{stock.ticker}: {exc}")
                logger.error("Error analysing %s: %s", stock.ticker, exc)

    await _maybe_send_report(today)


async def _maybe_send_report(date: object) -> None:
    from app.core.config import get_settings
    settings = get_settings()
    if not settings.WHATSAPP_ENABLED or not settings.WHATSAPP_TO:
        return
    try:
        from app.repositories.prediction import PredictionRepository
        from app.services.notification import send_report
        async with SessionLocal() as db:
            preds = await PredictionRepository(db).get_for_date(date)  # type: ignore[arg-type]
        await asyncio.to_thread(send_report, preds, settings)
        logger.info("WhatsApp report sent for %s", date)
    except Exception as exc:
        logger.error("WhatsApp report failed: %s", exc)
