import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_db
from models.prediction import Prediction
from models.watchlist import WatchlistStock
from schemas.watchlist import WatchlistStockCreate, WatchlistStockOut
from services.analysis import get_status, is_running, launch_analysis
from services.seed import INDEX_URLS, fetch_nse_index

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


# ── Watchlist CRUD ────────────────────────────────────────────────────────────

@router.post("/stocks", response_model=WatchlistStockOut, status_code=201)
async def add_stock(payload: WatchlistStockCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(WatchlistStock).where(WatchlistStock.ticker == payload.ticker)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"{payload.ticker} is already in the watchlist")
    stock = WatchlistStock(**payload.model_dump())
    db.add(stock)
    await db.commit()
    await db.refresh(stock)
    return stock


@router.get("/stocks", response_model=list[WatchlistStockOut])
async def list_stocks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WatchlistStock).order_by(WatchlistStock.created_at))
    return result.scalars().all()


@router.delete("/stocks/{ticker}")
async def remove_stock(ticker: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WatchlistStock).where(WatchlistStock.ticker == ticker.upper())
    )
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"{ticker} not found in watchlist")
    await db.delete(stock)
    await db.commit()
    return {"message": f"{ticker} removed from watchlist"}


# ── Signals (today's predictions) ────────────────────────────────────────────

@router.get("/signals")
async def get_todays_signals(db: AsyncSession = Depends(get_db)):
    """Today's predictions joined with watchlist name/exchange, sorted confidence desc."""
    today = datetime.date.today()

    result = await db.execute(
        select(Prediction, WatchlistStock.name, WatchlistStock.exchange)
        .join(WatchlistStock, WatchlistStock.ticker == Prediction.ticker, isouter=True)
        .where(Prediction.date == today)
        .order_by(Prediction.confidence.desc())
    )

    rows = result.all()
    output = []
    for pred, name, exchange in rows:
        d = {
            "id":                  pred.id,
            "ticker":              pred.ticker,
            "date":                pred.date.isoformat(),
            "signal":              pred.signal,
            "confidence":          pred.confidence,
            "predicted_direction": pred.predicted_direction,
            "target_low":          pred.target_low,
            "target_high":         pred.target_high,
            "reasoning":           pred.reasoning,
            "factors":             pred.factors,
            "limit_price":         pred.limit_price,
            "current_price":       pred.current_price,
            "actual_close":        pred.actual_close,
            "is_correct":          pred.is_correct,
            "generated_at":        pred.generated_at.isoformat() if pred.generated_at else None,
            "name":                name or pred.ticker,
            "exchange":            exchange or "",
        }
        output.append(d)
    return output


# ── Run analysis (async background) ──────────────────────────────────────────

@router.post("/run")
async def trigger_analysis(force: bool = False):
    """
    Start analysis for all watchlist stocks in the background.
    Returns immediately — poll /watchlist/run/status for progress.
    force=true re-runs stocks that already have a prediction today.
    """
    if is_running():
        raise HTTPException(status_code=409, detail="Analysis is already running")

    # Spawns a daemon thread with its own event loop — no greenlet conflicts
    launch_analysis(force=force)

    return {"status": "started", "message": "Analysis running in background"}


@router.delete("/stocks")
async def clear_all_stocks(db: AsyncSession = Depends(get_db)):
    """Remove every stock from the watchlist (used before seeding)."""
    await db.execute(WatchlistStock.__table__.delete())
    await db.commit()
    return {"message": "Watchlist cleared"}


@router.post("/seed")
async def seed_from_nse(index: str = "NIFTY50", db: AsyncSession = Depends(get_db)):
    """
    Bulk-load NSE index stocks into the watchlist.
    Skips tickers already present. Supported indices:
    NIFTY50, NIFTYNEXT50, NIFTY100, NIFTY200, NIFTY500, NIFTYIT, NIFTYBANK
    """
    if index.upper() not in INDEX_URLS:
        raise HTTPException(status_code=400, detail=f"Unknown index. Choose from: {list(INDEX_URLS)}")

    stocks = await fetch_nse_index(index)

    added = skipped = 0
    for s in stocks:
        existing = await db.execute(
            select(WatchlistStock).where(WatchlistStock.ticker == s["ticker"])
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        db.add(WatchlistStock(ticker=s["ticker"], name=s["name"], exchange=s["exchange"]))
        added += 1

    await db.commit()
    logger.info("Seeded %d stocks from %s (%d skipped)", added, index, skipped)
    return {"index": index, "added": added, "skipped": skipped, "total": added + skipped}


@router.get("/run/status")
async def analysis_status():
    """Poll this to track background analysis progress."""
    s = get_status()
    done = s["total"] - s["processed"] - s["skipped"] - s["errors"]
    return {
        **s,
        "pending": max(done, 0),
        "status":  "running" if s["running"] else "idle",
    }
