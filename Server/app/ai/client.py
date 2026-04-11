"""
Lazy singleton for the Anthropic async client.
Import get_client() wherever you need to call the API.
"""
from __future__ import annotations

from anthropic import AsyncAnthropic

_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        from app.core.config import get_settings
        _client = AsyncAnthropic(api_key=get_settings().ANTHROPIC_API_KEY)
    return _client
