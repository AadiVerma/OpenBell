"""
Twilio WhatsApp notification service.

All public functions are synchronous — call via asyncio.to_thread() in async context.
"""
from __future__ import annotations

import logging

from app.core.config import Settings
from app.models.prediction import Prediction
from app.services.report import build_report

logger = logging.getLogger(__name__)


def _normalize_whatsapp(number: str) -> str:
    """Ensure the number has the whatsapp: prefix."""
    if not number.startswith("whatsapp:"):
        return f"whatsapp:{number}"
    return number


def _client(settings: Settings):
    from twilio.rest import Client
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_report(predictions: list[Prediction], settings: Settings) -> None:
    """Send a formatted prediction report via WhatsApp."""
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise ValueError("Twilio credentials not configured")
    if not settings.WHATSAPP_TO:
        raise ValueError("WHATSAPP_TO not configured")

    client = _client(settings)
    from_num = _normalize_whatsapp(settings.TWILIO_FROM_NUMBER)
    to_num = _normalize_whatsapp(settings.WHATSAPP_TO)

    chunks = build_report(predictions, settings)
    for chunk in chunks:
        client.messages.create(body=chunk, from_=from_num, to=to_num)
        logger.info("Sent WhatsApp chunk (%d chars) → %s", len(chunk), to_num)


def send_test_message(settings: Settings) -> None:
    """Send a test message to verify Twilio configuration."""
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise ValueError("Twilio credentials not configured")
    if not settings.WHATSAPP_TO:
        raise ValueError("WHATSAPP_TO not configured")

    client = _client(settings)
    client.messages.create(
        body="✅ OpenBell test message — configuration working!",
        from_=_normalize_whatsapp(settings.TWILIO_FROM_NUMBER),
        to=_normalize_whatsapp(settings.WHATSAPP_TO),
    )
    logger.info("Test WhatsApp message sent to %s", settings.WHATSAPP_TO)
