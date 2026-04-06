from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker  # pyright: ignore[reportMissingImports]
from core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    connect_args={"statement_cache_size": 0},
)

SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
