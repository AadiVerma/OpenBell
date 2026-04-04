import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Float, Integer, Text, JSON, Boolean, Date, func
from sqlalchemy.orm import mapped_column, Mapped
from db.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)

    # LLM output
    signal: Mapped[str] = mapped_column(String(10), nullable=False)        # bullish/bearish/neutral
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)       # 0-100
    predicted_direction: Mapped[str] = mapped_column(String(10), nullable=False)  # up/down/neutral
    target_low: Mapped[float] = mapped_column(Float, nullable=False)
    target_high: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    factors: Mapped[dict] = mapped_column(JSON, nullable=False)            # list of {type, text}
    limit_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Market snapshot at prediction time
    current_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Outcome tracking (filled next day)
    actual_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    generated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
