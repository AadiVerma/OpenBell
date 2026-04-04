import datetime
from typing import Any, Optional
from pydantic import BaseModel


class PredictionOut(BaseModel):
    id: int
    ticker: str
    date: datetime.date
    signal: str
    confidence: int
    predicted_direction: str
    target_low: float
    target_high: float
    reasoning: str
    factors: Any
    limit_price: float
    current_price: float
    actual_close: Optional[float]
    is_correct: Optional[bool]
    generated_at: datetime.datetime

    model_config = {"from_attributes": True}


class PredictRequest(BaseModel):
    ticker: str
    name: str


class OutcomeUpdate(BaseModel):
    prediction_id: int
    actual_close: float
