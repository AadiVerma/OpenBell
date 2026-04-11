from __future__ import annotations

import asyncio
import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings, update_settings
from app.core.database import get_db
from app.repositories.prediction import PredictionRepository
from app.schemas.settings import AppSettingsOut, AppSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _mask(value: str, show_last: int = 4) -> str:
    if not value or len(value) <= show_last:
        return value
    return "*" * (len(value) - show_last) + value[-show_last:]


@router.get("/", response_model=AppSettingsOut)
async def get_app_settings():
    s = get_settings()
    return AppSettingsOut(
        whatsapp_enabled=s.WHATSAPP_ENABLED,
        whatsapp_to=s.WHATSAPP_TO,
        twilio_from_number=s.TWILIO_FROM_NUMBER,
        twilio_account_sid=_mask(s.TWILIO_ACCOUNT_SID),
        twilio_auth_token=_mask(s.TWILIO_AUTH_TOKEN),
        portfolio_budget=s.PORTFOLIO_BUDGET,
        anthropic_model=s.ANTHROPIC_MODEL,
    )


@router.patch("/", response_model=AppSettingsOut)
async def update_app_settings(body: AppSettingsUpdate):
    updates = body.model_dump(exclude_none=True)
    if updates:
        update_settings(**updates)
    return await get_app_settings()


@router.post("/test-whatsapp")
async def test_whatsapp():
    from app.services.notification import send_test_message
    s = get_settings()
    try:
        await asyncio.to_thread(send_test_message, s)
        return {"success": True, "message": "Test message sent"}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/send-report")
async def send_report_now(db: AsyncSession = Depends(get_db)):
    from app.services.notification import send_report
    s = get_settings()
    today = datetime.date.today()

    preds = await PredictionRepository(db).get_for_date(today)
    if not preds:
        yesterday = today - datetime.timedelta(days=1)
        preds = await PredictionRepository(db).get_for_date(yesterday)

    if not preds:
        raise HTTPException(404, "No predictions found for today or yesterday")

    try:
        await asyncio.to_thread(send_report, preds, s)
        return {"success": True, "predictions_sent": len(preds)}
    except Exception as exc:
        raise HTTPException(400, str(exc))
