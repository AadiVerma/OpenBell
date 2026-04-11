from __future__ import annotations

from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    whatsapp_enabled: bool
    whatsapp_to: str
    twilio_from_number: str
    twilio_account_sid: str   # masked in GET response
    twilio_auth_token: str    # masked in GET response
    portfolio_budget: float
    anthropic_model: str


class AppSettingsUpdate(BaseModel):
    whatsapp_enabled: bool | None = None
    whatsapp_to: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    portfolio_budget: float | None = None
