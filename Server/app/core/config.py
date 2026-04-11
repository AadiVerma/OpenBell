"""
Single source of truth for all configuration.

Base values come from .env (or environment variables).
Runtime-mutable settings (WhatsApp toggle, budget, Twilio credentials) can be
overridden at runtime through the Settings UI — overrides are persisted to
.settings.json (gitignored) and merged in on every call to get_settings().
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_OVERRIDES_FILE = Path(__file__).resolve().parent.parent.parent / ".settings.json"

# Fields the UI is allowed to override at runtime
_MUTABLE = {
    "whatsapp_enabled",
    "whatsapp_to",
    "twilio_account_sid",
    "twilio_auth_token",
    "twilio_from_number",
    "portfolio_budget",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost/openbell"

    # Anthropic — use Haiku for cost efficiency; swap to Sonnet for higher accuracy
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"

    # Market data
    FINNHUB_API_KEY: str = ""

    # Twilio / WhatsApp (overridable from Settings UI)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = "whatsapp:+14155238886"
    WHATSAPP_TO: str = ""
    WHATSAPP_ENABLED: bool = False

    # App behaviour (overridable from Settings UI)
    PORTFOLIO_BUDGET: float = 10000.0


def get_settings() -> Settings:
    """
    Return settings merged with any runtime overrides from .settings.json.
    Not cached — reads the override file on each call (small file, fast).
    """
    base = Settings()
    if not _OVERRIDES_FILE.exists():
        return base

    overrides = json.loads(_OVERRIDES_FILE.read_text())
    # Only apply keys that are in the mutable whitelist
    safe = {k: v for k, v in overrides.items() if k in _MUTABLE}
    if not safe:
        return base
    return base.model_copy(update={k.upper(): v for k, v in safe.items()})


def update_settings(**kwargs: object) -> None:
    """Persist mutable runtime overrides to .settings.json."""
    current: dict = {}
    if _OVERRIDES_FILE.exists():
        current = json.loads(_OVERRIDES_FILE.read_text())
    # Only store whitelisted keys
    current.update({k.lower(): v for k, v in kwargs.items() if k.lower() in _MUTABLE})
    _OVERRIDES_FILE.write_text(json.dumps(current, indent=2))
