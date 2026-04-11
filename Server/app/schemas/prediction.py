from __future__ import annotations

import datetime

from pydantic import BaseModel


class Factor(BaseModel):
    type: str
    text: str


class PredictionOut(BaseModel):
    id: int
    ticker: str
    date: datetime.date
    signal: str
    confidence: int
    predicted_direction: str
    target_low: float
    target_high: float
    limit_price: float
    current_price: float
    reasoning: str
    factors: list[Factor]
    actual_close: float | None
    is_correct: bool | None
    generated_at: datetime.datetime

    model_config = {"from_attributes": True}


class PredictRequest(BaseModel):
    ticker: str
    name: str
    exchange: str = "NSE"


class OutcomeUpdate(BaseModel):
    prediction_id: int
    actual_close: float
