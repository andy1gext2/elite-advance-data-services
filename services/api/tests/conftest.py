"""Test fixtures: an isolated in-memory SQLite DB + TestClient with dep overrides.

Env is forced before importing the app so the dev-lifespan never touches Postgres and
settings resolve to SQLite.
"""
from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "production")  # skip dev lifespan init_db()
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret")
# Valid Fernet key (urlsafe base64 of 32 bytes) so token encryption works in tests.
os.environ.setdefault("FERNET_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
# Never hit a real image/video API in tests — force the mocks even if .env sets a
# live provider.
os.environ["IMAGE_PROVIDER"] = "mock"
os.environ["VIDEO_PROVIDER"] = "mock"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models as _models  # noqa: E402,F401  (register tables on Base.metadata)
from app.ai.registry import get_ai_router  # noqa: E402
from app.ai.router import AIRouter  # noqa: E402
from app.ai.providers.mock import MockProvider  # noqa: E402
from app.core.db import Base, get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.services.plan_service import seed_default_plans  # noqa: E402


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared in-memory DB across connections
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    Base.metadata.create_all(bind=engine)
    with TestingSession() as db:
        seed_default_plans(db)
        db.commit()

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    # Never hit a real AI provider in tests — use the deterministic mock.
    fastapi_app.dependency_overrides[get_ai_router] = lambda: AIRouter(MockProvider())
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()
