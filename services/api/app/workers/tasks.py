"""Celery tasks. Thin wrappers around tenant-agnostic service functions so the
same logic is unit-testable without a broker (see tests/test_scheduling.py)."""
from __future__ import annotations

from app.core.db import SessionLocal
from app.services.scheduling_service import run_due
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.publish_due")
def publish_due() -> dict:
    """Beat-scheduled: publish every schedule across all tenants whose time has come."""
    with SessionLocal() as db:
        summary = run_due(db)
        db.commit()
        return summary
