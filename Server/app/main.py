"""
OpenBell — LLM-powered next-day stock signal generator.

Entry point: uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.routers import predictions, settings, watchlist

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (idempotent — safe to run every time)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="OpenBell",
    description="LLM-powered next-day stock signal generator for Indian & global markets.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All routers are mounted without an /api prefix here.
# The Vite dev proxy strips /api before forwarding to FastAPI, so the paths match.
app.include_router(watchlist.router)
app.include_router(predictions.router)
app.include_router(settings.router)


@app.get("/", tags=["health"])
async def health():
    return {"status": "ok", "service": "OpenBell"}
