from contextlib import asynccontextmanager
from fastapi import FastAPI
from db.base import Base
from db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

# app.include_router(your_router)
