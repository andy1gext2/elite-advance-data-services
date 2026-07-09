"""Database engine, session, and declarative base.

Portable across PostgreSQL (prod) and SQLite (local dev/tests) — models use
SQLAlchemy generic types so the same schema works on both.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.sqlalchemy_url.startswith("sqlite")

engine = create_engine(
    settings.sqlalchemy_url,
    pool_pre_ping=True,
    # SQLite needs this to be usable across FastAPI's threads.
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency: a request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Dev convenience: create tables + seed plans.

    Prod uses Alembic migrations (see migrations/). create_all is a no-op for
    existing tables, so it is safe to call on startup for a fresh dev DB.
    """
    from app import models  # noqa: F401  (register models on Base.metadata)
    from app.services.plan_service import seed_default_plans

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_default_plans(db)
        db.commit()
