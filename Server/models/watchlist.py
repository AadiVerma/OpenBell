import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import mapped_column, Mapped
from db.base import Base


class WatchlistStock(Base):
    __tablename__ = "watchlist_stocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
