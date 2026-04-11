"""
All database access for WatchlistStock records lives here.
"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.watchlist import WatchlistStock


class WatchlistRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self) -> list[WatchlistStock]:
        result = await self._db.execute(
            select(WatchlistStock).order_by(WatchlistStock.ticker)
        )
        return list(result.scalars().all())

    async def get_by_ticker(self, ticker: str) -> WatchlistStock | None:
        result = await self._db.execute(
            select(WatchlistStock).where(WatchlistStock.ticker == ticker)
        )
        return result.scalar_one_or_none()

    async def create(self, ticker: str, name: str, exchange: str = "NSE") -> WatchlistStock:
        stock = WatchlistStock(ticker=ticker, name=name, exchange=exchange)
        self._db.add(stock)
        await self._db.commit()
        await self._db.refresh(stock)
        return stock

    async def delete(self, ticker: str) -> bool:
        result = await self._db.execute(
            delete(WatchlistStock).where(WatchlistStock.ticker == ticker)
        )
        await self._db.commit()
        return result.rowcount > 0

    async def delete_all(self) -> int:
        result = await self._db.execute(delete(WatchlistStock))
        await self._db.commit()
        return result.rowcount

    async def bulk_create(self, stocks: list[dict]) -> int:
        """Insert stocks, silently skip duplicates by ticker."""
        count = 0
        for s in stocks:
            existing = await self.get_by_ticker(s["ticker"])
            if not existing:
                self._db.add(WatchlistStock(**s))
                count += 1
        await self._db.commit()
        return count
