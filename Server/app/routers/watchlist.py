from __future__ import annotations

import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.prediction import PredictionRepository
from app.repositories.watchlist import WatchlistRepository
from app.schemas.prediction import PredictionOut
from app.schemas.watchlist import WatchlistStockCreate, WatchlistStockOut
from app.services.orchestrator import get_job_state, run_analysis
from app.services.seed import fetch_index_tickers

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("/stocks", response_model=list[WatchlistStockOut])
async def list_stocks(db: AsyncSession = Depends(get_db)):
    return await WatchlistRepository(db).get_all()


@router.post("/stocks", response_model=WatchlistStockOut, status_code=201)
async def add_stock(body: WatchlistStockCreate, db: AsyncSession = Depends(get_db)):
    repo = WatchlistRepository(db)
    if await repo.get_by_ticker(body.ticker):
        raise HTTPException(409, f"{body.ticker} already in watchlist")
    return await repo.create(ticker=body.ticker, name=body.name, exchange=body.exchange)


@router.delete("/stocks/{ticker}", status_code=204)
async def remove_stock(ticker: str, db: AsyncSession = Depends(get_db)):
    deleted = await WatchlistRepository(db).delete(ticker)
    if not deleted:
        raise HTTPException(404, f"{ticker} not found")


@router.delete("/stocks", status_code=204)
async def clear_watchlist(db: AsyncSession = Depends(get_db)):
    await WatchlistRepository(db).delete_all()


@router.post("/seed")
async def seed_from_index(
    index: str = Query("NIFTY50"),
    db: AsyncSession = Depends(get_db),
):
    tickers = fetch_index_tickers(index)
    if not tickers:
        raise HTTPException(404, f"No tickers found for index '{index}'")
    added = await WatchlistRepository(db).bulk_create(tickers)
    return {"added": added, "total": len(tickers), "index": index}


@router.get("/signals", response_model=list[PredictionOut])
async def get_signals(db: AsyncSession = Depends(get_db)):
    return await PredictionRepository(db).get_for_date(datetime.date.today())


@router.post("/run")
async def trigger_analysis(
    background_tasks: BackgroundTasks,
    force: bool = Query(False),
):
    background_tasks.add_task(run_analysis, force)
    return {"status": "started", "force": force}


@router.get("/run/status")
async def analysis_status():
    return get_job_state()
