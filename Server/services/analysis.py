"""Background analysis — runs in a dedicated thread + event loop to avoid
SQLAlchemy greenlet conflicts with asyncio.create_task()."""
import asyncio
import datetime
import logging
import threading

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import select

from core.config import settings
from models.prediction import Prediction
from models.watchlist import WatchlistStock
from services.llm import predict_stock
from services.market_data import get_stock_data
from services.news import get_stock_news

logger = logging.getLogger(__name__)

# ── In-memory job state ───────────────────────────────────────────────────────
_state: dict = {
    "running":     False,
    "total":       0,
    "processed":   0,
    "skipped":     0,
    "errors":      0,
    "current":     None,
    "started_at":  None,
    "finished_at": None,
    "last_error":  None,
}


def get_status() -> dict:
    return dict(_state)


def is_running() -> bool:
    return _state["running"]


def mark_started() -> None:
    _state.update({
        "running": True, "total": 0, "processed": 0,
        "skipped": 0, "errors": 0, "current": None,
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "finished_at": None, "last_error": None,
    })


# ── Core analysis logic ───────────────────────────────────────────────────────

async def _analyse(force: bool) -> None:
    """Runs inside the background thread's own event loop with its own engine."""
    # NullPool: no shared connection pool — each run gets fresh connections
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False)

    try:
        async with Session() as db:
            stocks_result = await db.execute(select(WatchlistStock))
            stocks = stocks_result.scalars().all()
            today = datetime.date.today()
            _state["total"] = len(stocks)
            logger.info("Starting analysis for %d stocks", len(stocks))

            for stock in stocks:
                _state["current"] = stock.ticker
                async with Session() as sdb:   # fresh session per stock
                    try:
                        if force:
                            existing = await sdb.execute(
                                select(Prediction).where(
                                    Prediction.ticker == stock.ticker,
                                    Prediction.date == today,
                                )
                            )
                            row = existing.scalar_one_or_none()
                            if row:
                                await sdb.delete(row)
                                await sdb.commit()

                        if not force:
                            existing = await sdb.execute(
                                select(Prediction).where(
                                    Prediction.ticker == stock.ticker,
                                    Prediction.date == today,
                                )
                            )
                            if existing.scalar_one_or_none():
                                _state["skipped"] += 1
                                logger.info("Skip %s — already predicted today", stock.ticker)
                                continue

                        market_data = await get_stock_data(stock.ticker)
                        if not market_data:
                            logger.warning("No market data for %s", stock.ticker)
                            _state["errors"] += 1
                            continue

                        news = await get_stock_news(stock.ticker, stock.name)
                        prediction = await predict_stock(stock.ticker, market_data, news)

                        sdb.add(Prediction(
                            ticker=stock.ticker,
                            date=today,
                            signal=prediction.signal,
                            confidence=prediction.confidence,
                            predicted_direction=prediction.predicted_direction,
                            target_low=prediction.target_low,
                            target_high=prediction.target_high,
                            reasoning=prediction.reasoning,
                            factors=prediction.factors,
                            limit_price=prediction.limit_price,
                            current_price=market_data["current_price"],
                        ))
                        await sdb.commit()
                        _state["processed"] += 1
                        logger.info("✓ %s  %s  %d%%",
                                    stock.ticker, prediction.signal, prediction.confidence)

                    except Exception as exc:
                        logger.error("✗ %s: %s", stock.ticker, exc, exc_info=True)
                        _state["errors"] += 1
                        _state["last_error"] = f"{stock.ticker}: {exc}"
                        # session context manager auto-rolls back on exit

    except Exception as exc:
        logger.error("Analysis outer error: %s", exc, exc_info=True)
        _state["last_error"] = str(exc)
    finally:
        await engine.dispose()
        _state["running"]     = False
        _state["current"]     = None
        _state["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        logger.info("Analysis done — processed=%d skipped=%d errors=%d",
                    _state["processed"], _state["skipped"], _state["errors"])


# ── Public launcher — call from sync route handler ───────────────────────────

def launch_analysis(force: bool = False) -> None:
    """
    Spawn a daemon thread with its own event loop.
    Completely isolated from FastAPI's event loop → no greenlet issues.
    """
    if _state["running"]:
        logger.warning("Already running — ignoring duplicate launch")
        return

    mark_started()

    def _thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_analyse(force))
        except Exception as exc:
            logger.error("Thread-level error: %s", exc, exc_info=True)
            _state["last_error"] = str(exc)
            _state["running"]    = False
        finally:
            loop.close()

    threading.Thread(target=_thread, daemon=True, name="openbell-analysis").start()
    logger.info("Analysis thread launched (force=%s)", force)
