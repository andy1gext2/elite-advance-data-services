"""Celery tasks. Thin wrappers around tenant-agnostic service functions so the
same logic is unit-testable without a broker (see tests/test_scheduling.py)."""
from __future__ import annotations

from app.ai.registry import get_ai_router
from app.core.db import SessionLocal
from app.services.campaign_service import run_autopilot
from app.services.reputation_service import poll_all_businesses
from app.services.scheduling_service import run_due
from app.services.video_service import advance_processing_jobs
from app.storage.registry import get_storage
from app.video.registry import get_video_provider
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.publish_due")
def publish_due() -> dict:
    """Beat-scheduled: publish every schedule across all tenants whose time has come."""
    with SessionLocal() as db:
        summary = run_due(db)
        db.commit()
        return summary


@celery_app.task(name="app.workers.tasks.propose_campaigns")
def propose_campaigns() -> dict:
    """Beat-scheduled: draft campaigns for autopilot tenants whose cadence is due.
    Proposals wait for human approval (approve-first)."""
    with SessionLocal() as db:
        summary = run_autopilot(db, router=get_ai_router())
        db.commit()
        return summary


@celery_app.task(name="app.workers.tasks.poll_reviews")
def poll_reviews() -> dict:
    """Beat-scheduled: sync new reviews for every tenant with a connected account,
    so reputation stays current without anyone clicking 'Sync'. Platforms whose
    connector can't read reviews yet are skipped."""
    with SessionLocal() as db:
        summary = poll_all_businesses(db)
        db.commit()
        return summary


@celery_app.task(name="app.workers.tasks.advance_video_jobs")
def advance_video_jobs() -> dict:
    """Beat-scheduled: poll in-flight Veo renders and finish any that are ready, so
    videos complete server-side without the browser polling."""
    with SessionLocal() as db:
        summary = advance_processing_jobs(
            db, provider=get_video_provider(), storage=get_storage()
        )
        db.commit()
        return summary
