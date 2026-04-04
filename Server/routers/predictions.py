import asyncio
import datetime
import logging

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_db
from models.prediction import Prediction
from schemas.prediction import OutcomeUpdate, PredictRequest, PredictionOut
from services.llm import predict_stock
from services.market_data import get_stock_data
from services.news import get_stock_news, _is_indian

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("/news/{ticker}")
async def fetch_news(
    ticker: str,
    name: str = Query(default="", description="Company name (improves Indian stock search)"),
):
    """Fetch latest news for any ticker. Useful for testing before running a prediction."""
    articles = await get_stock_news(ticker.upper(), name)
    return {
        "ticker": ticker.upper(),
        "source": "Google News RSS" if _is_indian(ticker) else "Finnhub",
        "count": len(articles),
        "articles": articles,
    }


@router.post("/predict", response_model=PredictionOut, status_code=201)
async def predict_single(payload: PredictRequest, db: AsyncSession = Depends(get_db)):
    """Ad-hoc prediction for any stock. Fetches live data and calls Claude."""
    market_data = await get_stock_data(payload.ticker)
    if not market_data:
        raise HTTPException(status_code=400, detail=f"Could not fetch market data for {payload.ticker}")

    news = await get_stock_news(payload.ticker, payload.name)
    prediction = await predict_stock(payload.ticker, market_data, news)

    db_pred = Prediction(
        ticker=prediction.ticker,
        date=datetime.date.today(),
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
    db.add(db_pred)
    await db.commit()
    await db.refresh(db_pred)
    return db_pred


@router.get("/history", response_model=list[PredictionOut])
async def get_history(
    ticker: str | None = Query(default=None, description="Filter by ticker"),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Past predictions, newest first. Optionally filter by ticker."""
    query = select(Prediction).order_by(Prediction.generated_at.desc()).limit(limit)
    if ticker:
        query = query.where(Prediction.ticker == ticker.upper())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/accuracy")
async def get_accuracy(
    ticker: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Accuracy stats for resolved predictions."""
    query = select(Prediction).where(Prediction.is_correct.is_not(None))
    if ticker:
        query = query.where(Prediction.ticker == ticker.upper())
    result = await db.execute(query)
    preds = result.scalars().all()

    if not preds:
        return {"total": 0, "correct": 0, "accuracy_pct": None}

    correct = sum(1 for p in preds if p.is_correct)
    return {
        "total": len(preds),
        "correct": correct,
        "accuracy_pct": round(correct / len(preds) * 100, 1),
    }


@router.post("/outcome")
async def record_outcome(payload: OutcomeUpdate, db: AsyncSession = Depends(get_db)):
    """Record the actual next-day close to track prediction accuracy."""
    result = await db.execute(select(Prediction).where(Prediction.id == payload.prediction_id))
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")

    pred.actual_close = payload.actual_close

    price_change_pct = (payload.actual_close - pred.current_price) / pred.current_price
    if pred.predicted_direction == "up":
        pred.is_correct = price_change_pct > 0.002     # >0.2% counts as "up"
    elif pred.predicted_direction == "down":
        pred.is_correct = price_change_pct < -0.002    # <-0.2% counts as "down"
    else:
        pred.is_correct = abs(price_change_pct) <= 0.005  # ±0.5% counts as "neutral"

    await db.commit()
    return {"prediction_id": pred.id, "is_correct": pred.is_correct, "change_pct": round(price_change_pct * 100, 2)}


# ── Auto-verify: fetch actual closes from yfinance ────────────────────────────

def _next_trading_date(from_date: datetime.date) -> datetime.date:
    """Return the next calendar day that is Mon–Fri (skips weekends only; holidays not handled)."""
    d = from_date + datetime.timedelta(days=1)
    while d.weekday() >= 5:   # 5=Saturday, 6=Sunday
        d += datetime.timedelta(days=1)
    return d


def _fetch_next_close(ticker: str, prediction_date: datetime.date) -> float | None:
    """
    Fetch the actual closing price for the first trading day AFTER prediction_date.
    Returns None if that date hasn't happened yet (future date).
    """
    next_day = _next_trading_date(prediction_date)
    today    = datetime.date.today()

    if next_day > today:
        logger.info("%s: next trading day %s is in the future — cannot verify yet", ticker, next_day)
        return None

    try:
        end  = next_day + datetime.timedelta(days=1)
        hist = yf.Ticker(ticker).history(start=str(next_day), end=str(end))
        if hist.empty:
            # Try one more day (market holiday)
            next_day2 = _next_trading_date(next_day)
            end2      = next_day2 + datetime.timedelta(days=1)
            hist      = yf.Ticker(ticker).history(start=str(next_day2), end=str(end2))
        if hist.empty:
            return None
        return float(hist["Close"].iloc[0])
    except Exception as e:
        logger.warning("Could not fetch actual close for %s on %s: %s", ticker, prediction_date, e)
        return None


def _mark_correct(pred: Prediction, actual_close: float) -> None:
    pred.actual_close = actual_close
    change_pct = (actual_close - pred.current_price) / pred.current_price
    if pred.predicted_direction == "up":
        pred.is_correct = change_pct > 0.002
    elif pred.predicted_direction == "down":
        pred.is_correct = change_pct < -0.002
    else:
        pred.is_correct = abs(change_pct) <= 0.005


@router.post("/verify")
async def verify_predictions(
    date: str | None = Query(default=None, description="YYYY-MM-DD (default: yesterday)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-fetch actual next-day closing prices from yfinance and mark
    each prediction on `date` as correct/incorrect.
    """
    if date:
        target_date = datetime.date.fromisoformat(date)
    else:
        # Default to yesterday
        target_date = datetime.date.today() - datetime.timedelta(days=1)

    result = await db.execute(
        select(Prediction).where(
            Prediction.date == target_date,
            Prediction.actual_close.is_(None),
        )
    )
    predictions = result.scalars().all()

    next_trading = _next_trading_date(target_date)
    today        = datetime.date.today()

    if next_trading > today:
        return {
            "date":             str(target_date),
            "next_trading_day": str(next_trading),
            "verified":         0,
            "not_yet":          True,
            "message":          f"Next trading day after {target_date} is {next_trading} — market hasn't closed yet.",
        }

    if not predictions:
        return {"date": str(target_date), "verified": 0, "already_done": True}

    loop = asyncio.get_event_loop()
    verified = errors = 0

    for pred in predictions:
        actual = await loop.run_in_executor(None, _fetch_next_close, pred.ticker, target_date)
        if actual is not None:
            _mark_correct(pred, actual)
            verified += 1
            logger.info("Verified %s: predicted=%s actual=%.2f correct=%s",
                        pred.ticker, pred.predicted_direction, actual, pred.is_correct)
        else:
            errors += 1

    await db.commit()
    return {
        "date":             str(target_date),
        "next_trading_day": str(next_trading),
        "verified":         verified,
        "errors":           errors,
    }


@router.get("/backtest")
async def get_backtest(
    days: int = Query(default=14, le=90),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns verified predictions (with actual closes) for the last `days` days.
    Used to render the accuracy chart.
    """
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    result = await db.execute(
        select(Prediction)
        .where(Prediction.date >= cutoff)
        .where(Prediction.actual_close.is_not(None))
        .order_by(Prediction.date.asc(), Prediction.confidence.desc())
    )
    preds = result.scalars().all()

    output = []
    for p in preds:
        actual_chg = round((p.actual_close - p.current_price) / p.current_price * 100, 2)
        target_mid = round((p.target_low + p.target_high) / 2, 2) if p.target_low and p.target_high else None
        predicted_chg = round((target_mid - p.current_price) / p.current_price * 100, 2) if target_mid else 0
        output.append({
            "id":               p.id,
            "ticker":           p.ticker.replace(".NS", "").replace(".BO", ""),
            "date":             str(p.date),
            "signal":           p.signal,
            "confidence":       p.confidence,
            "predicted_direction": p.predicted_direction,
            "current_price":    p.current_price,
            "target_low":       p.target_low,
            "target_high":      p.target_high,
            "actual_close":     p.actual_close,
            "is_correct":       p.is_correct,
            "actual_chg_pct":   actual_chg,
            "predicted_chg_pct": predicted_chg,
        })
    return output
