"""Idempotently seed the default plans. Run after migrations on deploy.

In dev the app seeds plans on startup; in production the app uses Alembic and
skips that, so the deploy start command runs this once (safe to re-run)."""
from __future__ import annotations

from app.core.db import SessionLocal
from app.services.plan_service import seed_default_plans


def main() -> None:
    with SessionLocal() as db:
        seed_default_plans(db)
        db.commit()
    print("plans seeded (idempotent)")


if __name__ == "__main__":
    main()
