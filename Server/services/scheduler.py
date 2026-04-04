import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import SessionLocal
from models.prediction import Prediction
from models.watchlist import WatchlistStock
from services.llm import predict_stock
from services.market_data import get_stock_data
from services.news import get_stock_news

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")


async def run_daily_analysis(db: AsyncSession | None = None) -> dict:
    """Run LLM prediction for every stock in the watchlist.

    Returns a summary dict with counts.
    """
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    results = {"processed": 0, "skipped": 0, "errors": 0}

    try:
        stocks_result = await db.execute(select(WatchlistStock))
        stocks = stocks_result.scalars().all()
        today = datetime.date.today()

        for stock in stocks:
            try:
                # Skip if already predicted today
                existing = await db.execute(
                    select(Prediction).where(
                        Prediction.ticker == stock.ticker,
                        Prediction.date == today,
                    )
                )
                if existing.scalar_one_or_none():
                    results["skipped"] += 1
                    continue

                market_data = await get_stock_data(stock.ticker)
                if not market_data:
                    logger.warning("No market data for %s — skipping", stock.ticker)
                    results["errors"] += 1
                    continue

                news = await get_stock_news(stock.ticker, stock.name)
                prediction = await predict_stock(stock.ticker, market_data, news)

                db.add(
                    Prediction(
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
                    )
                )
                await db.commit()
                results["processed"] += 1
                logger.info("Prediction saved for %s (signal=%s, confidence=%d%%)",
                            stock.ticker, prediction.signal, prediction.confidence)

            except Exception as exc:
                logger.error("Error processing %s: %s", stock.ticker, exc)
                await db.rollback()
                results["errors"] += 1

    finally:
        if owns_session:
            await db.aclose()

    return results


async def _scheduled_job() -> None:
    logger.info("Running scheduled daily stock analysis")
    results = await run_daily_analysis()
    logger.info("Scheduled analysis complete: %s", results)


def start_scheduler() -> None:
    # 4:30 PM IST = market closes at 3:30 PM, give 1 hour buffer
    scheduler.add_job(
        _scheduled_job,
        trigger="cron",
        hour=16,
        minute=30,
        id="daily_analysis",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — daily analysis at 4:30 PM IST")
