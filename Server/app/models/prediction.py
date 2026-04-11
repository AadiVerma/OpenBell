from __future__ import annotations

import datetime

from sqlalchemy import Date, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (Index("ix_predictions_ticker_date", "ticker", "date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)

    # AI output
    signal: Mapped[str] = mapped_column(String(10))           # bullish | bearish | neutral
    confidence: Mapped[int] = mapped_column(Integer)           # 0–100
    predicted_direction: Mapped[str] = mapped_column(String(10))  # up | down | neutral
    target_low: Mapped[float] = mapped_column(Float)
    target_high: Mapped[float] = mapped_column(Float)
    limit_price: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)
    factors: Mapped[list] = mapped_column(JSONB, default=list)

    # Market snapshot captured at prediction time
    current_price: Mapped[float] = mapped_column(Float)

    # Outcome — filled in the next trading day
    actual_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)

    generated_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
