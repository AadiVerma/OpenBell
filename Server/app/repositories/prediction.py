"""
All database access for Prediction records lives here.
Services and routers must NOT import SQLAlchemy directly — use this repository.
"""
from __future__ import annotations

import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import Prediction


class PredictionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, **kwargs) -> Prediction:
        pred = Prediction(**kwargs)
        self._db.add(pred)
        await self._db.commit()
        await self._db.refresh(pred)
        return pred

    async def get_by_id(self, prediction_id: int) -> Prediction | None:
        result = await self._db.execute(
            select(Prediction).where(Prediction.id == prediction_id)
        )
        return result.scalar_one_or_none()

    async def get_today(self, ticker: str, date: datetime.date) -> Prediction | None:
        result = await self._db.execute(
            select(Prediction).where(
                and_(Prediction.ticker == ticker, Prediction.date == date)
            )
        )
        return result.scalar_one_or_none()

    async def get_for_date(self, date: datetime.date) -> list[Prediction]:
        result = await self._db.execute(
            select(Prediction)
            .where(Prediction.date == date)
            .order_by(Prediction.confidence.desc())
        )
        return list(result.scalars().all())

    async def get_history(
        self, ticker: str | None = None, limit: int = 50
    ) -> list[Prediction]:
        q = select(Prediction).order_by(Prediction.generated_at.desc()).limit(limit)
        if ticker:
            q = q.where(Prediction.ticker == ticker)
        result = await self._db.execute(q)
        return list(result.scalars().all())

    async def get_unverified(self, date: datetime.date) -> list[Prediction]:
        result = await self._db.execute(
            select(Prediction).where(
                and_(Prediction.date == date, Prediction.actual_close.is_(None))
            )
        )
        return list(result.scalars().all())

    async def get_backtest(self, days: int = 14) -> list[Prediction]:
        cutoff = datetime.date.today() - datetime.timedelta(days=days)
        result = await self._db.execute(
            select(Prediction)
            .where(
                and_(
                    Prediction.date >= cutoff,
                    Prediction.actual_close.is_not(None),
                )
            )
            .order_by(Prediction.date.desc())
        )
        return list(result.scalars().all())

    async def update_outcome(
        self, prediction_id: int, actual_close: float, is_correct: bool
    ) -> Prediction | None:
        pred = await self.get_by_id(prediction_id)
        if not pred:
            return None
        pred.actual_close = actual_close
        pred.is_correct = is_correct
        await self._db.commit()
        await self._db.refresh(pred)
        return pred

    async def get_accuracy(self, ticker: str | None = None) -> dict:
        q = select(Prediction).where(Prediction.actual_close.is_not(None))
        if ticker:
            q = q.where(Prediction.ticker == ticker)
        result = await self._db.execute(q)
        preds = list(result.scalars().all())
        total = len(preds)
        correct = sum(1 for p in preds if p.is_correct)
        return {
            "total": total,
            "correct": correct,
            "accuracy_pct": round(correct / total * 100, 1) if total else 0.0,
        }
