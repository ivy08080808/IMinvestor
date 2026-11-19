"""FastAPI application entry point.

Run from ``backend/``::

    uvicorn app.main:app --port 8000

Interactive API docs: http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db, scheduler
from app.config import settings
from app.errors import install_handlers
from app.routers import admin, auth, market, orders, quotes, watchlist

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Open the DB pool and start the 15:00 scheduler for the app's lifetime."""
    db.init_pool()
    if settings.scheduler_enabled:
        scheduler.start()
    yield
    scheduler.shutdown()
    db.close_pool()


app = FastAPI(title="IMinvestor API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_handlers(app)

for r in (auth.router, market.router, quotes.router, watchlist.router, orders.router, admin.router):
    app.include_router(r)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    """Liveness probe."""
    return {"ok": True}
