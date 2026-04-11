from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

_settings = get_settings()

_is_pooler = ":6543/" in _settings.DATABASE_URL  # Supabase PgBouncer port

engine = create_async_engine(
    _settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    # PgBouncer (Supabase pooler port 6543) runs in transaction mode and does not
    # support prepared statements. Disable the cache to avoid the "prepared statement
    # does not exist" error. No-op when using a direct connection.
    connect_args={"statement_cache_size": 0} if _is_pooler else {},
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
