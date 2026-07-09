"""FastAPI application entrypoint.

Runnable today:  uvicorn app.main:app --reload  ->  http://127.0.0.1:8000/docs

This is the skeleton. Domain routers (auth, businesses, content, reviews, ...)
are added per docs/roadmap.md. Keep routers thin; put logic in app/services.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    analytics,
    auth,
    businesses,
    calendar,
    content,
    oauth,
    reputation,
    scheduling,
)
from app.core.config import get_settings
from app.core.db import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: ensure tables exist and plans are seeded.
    # In production, schema is managed by Alembic migrations instead.
    if not settings.is_production:
        init_db()
    yield


app = FastAPI(
    title="Elite Advance Data Services API",
    version="0.1.0",
    description="AI Marketing & Reputation Management platform — backend API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(businesses.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")
app.include_router(scheduling.router, prefix="/api/v1")
app.include_router(calendar.router, prefix="/api/v1")
app.include_router(reputation.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(oauth.router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "env": settings.app_env, "version": app.version}


@app.get("/", tags=["system"])
def root() -> dict:
    return {"service": "elite-advance-data-services", "docs": "/docs"}


# Future phases register more routers here (content, calendar, reviews, ...).
