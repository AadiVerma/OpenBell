from __future__ import annotations

import datetime

from pydantic import BaseModel


class WatchlistStockCreate(BaseModel):
    ticker: str
    name: str
    exchange: str = "NSE"


class WatchlistStockOut(BaseModel):
    id: int
    ticker: str
    name: str
    exchange: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
