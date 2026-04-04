from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.base import Base
from db.session import engine
import models  # noqa: F401 — registers all models with Base.metadata
from routers.watchlist import router as watchlist_router
from routers.predictions import router as predictions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="OpenBell — Stock Prediction API",
    description="LLM-powered next-day stock signal generator.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(watchlist_router)
app.include_router(predictions_router)


@app.get("/", tags=["Health"])
async def health():
    return {"status": "ok", "service": "OpenBell"}
