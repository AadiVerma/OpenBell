from __future__ import annotations

import asyncio
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.analyzer import analyze_stock
from app.core.database import get_db
from app.repositories.prediction import PredictionRepository
from app.schemas.prediction import OutcomeUpdate, PredictRequest, PredictionOut
from app.services.excel import generate_excel
from app.services.market_data import fetch_market_data
from app.services.news import fetch_news

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/predict", response_model=PredictionOut, status_code=201)
async def predict(body: PredictRequest, db: AsyncSession = Depends(get_db)):
    market_data = await asyncio.to_thread(fetch_market_data, body.ticker)
    if not market_data:
        raise HTTPException(422, f"Could not fetch market data for '{body.ticker}'")

    news = await asyncio.to_thread(fetch_news, body.ticker)
    pred = await analyze_stock(body.ticker, market_data, news)

    return await PredictionRepository(db).create(
        ticker=body.ticker,
        date=datetime.date.today(),
        signal=pred.signal,
        confidence=pred.confidence,
        predicted_direction=pred.predicted_direction,
        target_low=pred.target_low,
        target_high=pred.target_high,
        limit_price=pred.limit_price,
        reasoning=pred.reasoning,
        factors=pred.factors,
        current_price=market_data["current_price"],
    )


@router.get("/history", response_model=list[PredictionOut])
async def history(
    ticker: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await PredictionRepository(db).get_history(ticker, limit)


@router.get("/accuracy")
async def accuracy(
    ticker: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await PredictionRepository(db).get_accuracy(ticker)


@router.post("/outcome")
async def record_outcome(body: OutcomeUpdate, db: AsyncSession = Depends(get_db)):
    repo = PredictionRepository(db)
    pred = await repo.get_by_id(body.prediction_id)
    if not pred:
        raise HTTPException(404, "Prediction not found")

    change_pct = (body.actual_close - pred.current_price) / pred.current_price * 100
    if pred.predicted_direction == "up":
        is_correct = change_pct > 0.2
    elif pred.predicted_direction == "down":
        is_correct = change_pct < -0.2
    else:
        is_correct = abs(change_pct) <= 0.5

    await repo.update_outcome(body.prediction_id, body.actual_close, is_correct)
    return {
        "success": True,
        "is_correct": is_correct,
        "change_pct": round(change_pct, 2),
    }


@router.post("/verify")
async def verify_predictions(
    date: str = Query(..., description="ISO date string, e.g. 2025-01-15"),
    db: AsyncSession = Depends(get_db),
):
    target = datetime.date.fromisoformat(date)
    next_day = _next_trading_day(target)

    if next_day > datetime.date.today():
        return {
            "status": "pending",
            "message": f"Next trading day ({next_day}) hasn't arrived yet",
            "next_trading_day": next_day.isoformat(),
        }

    repo = PredictionRepository(db)
    unverified = await repo.get_unverified(target)
    updated = 0

    for pred in unverified:
        actual = await asyncio.to_thread(_fetch_close, pred.ticker, next_day)
        if actual is None:
            continue
        change_pct = (actual - pred.current_price) / pred.current_price * 100
        if pred.predicted_direction == "up":
            is_correct = change_pct > 0.2
        elif pred.predicted_direction == "down":
            is_correct = change_pct < -0.2
        else:
            is_correct = abs(change_pct) <= 0.5
        await repo.update_outcome(pred.id, actual, is_correct)
        updated += 1

    return {"verified": updated, "total": len(unverified), "date": date}


@router.get("/backtest")
async def backtest(
    days: int = Query(14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    preds = await PredictionRepository(db).get_backtest(days)
    return [
        {
            "id": p.id,
            "ticker": p.ticker,
            "date": p.date.isoformat(),
            "signal": p.signal,
            "confidence": p.confidence,
            "predicted_direction": p.predicted_direction,
            "current_price": p.current_price,
            "actual_close": p.actual_close,
            "is_correct": p.is_correct,
            "price_delta_pct": (
                round((p.actual_close - p.current_price) / p.current_price * 100, 2)
                if p.actual_close
                else None
            ),
        }
        for p in preds
    ]


@router.get("/news/{ticker}")
async def get_news(ticker: str):
    return await asyncio.to_thread(fetch_news, ticker)


@router.get("/report.xlsx")
async def download_report(
    date: str = Query(default_factory=lambda: datetime.date.today().isoformat()),
    db: AsyncSession = Depends(get_db),
):
    from app.core.config import get_settings
    target = datetime.date.fromisoformat(date)
    preds = await PredictionRepository(db).get_for_date(target)
    xlsx = generate_excel(preds, target, get_settings())
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=openbell_{date}.xlsx"},
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _next_trading_day(d: datetime.date) -> datetime.date:
    """Return next weekday after d (ignores public holidays)."""
    nxt = d + datetime.timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += datetime.timedelta(days=1)
    return nxt


def _fetch_close(ticker: str, date: datetime.date) -> float | None:
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(
            start=date.isoformat(),
            end=(date + datetime.timedelta(days=1)).isoformat(),
        )
        if hist.empty:
            return None
        return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        return None
