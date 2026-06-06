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
        if not stocks:
            return 0
            
        tickers = [s["ticker"] for s in stocks]
        result = await self._db.execute(
            select(WatchlistStock.ticker).where(WatchlistStock.ticker.in_(tickers))
        )
        existing_tickers = set(result.scalars().all())
        
        to_insert = [s for s in stocks if s["ticker"] not in existing_tickers]
        if to_insert:
            self._db.add_all([WatchlistStock(**s) for s in to_insert])
            await self._db.commit()
            
        return len(to_insert)
