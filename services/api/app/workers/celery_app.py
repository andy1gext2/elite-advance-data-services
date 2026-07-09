"""Celery app + beat schedule.

Runs the publish engine on a cadence. Requires a Redis broker (see docker-compose
or a hosted Redis). On Windows, start the worker with `--pool=solo` (the default
prefork pool is unreliable there), or run it in WSL/Docker/Linux:

    celery -A app.workers.celery_app worker --beat --loglevel=info --pool=solo
"""
from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "elite",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    timezone="UTC",
    beat_schedule={
        "publish-due-every-minute": {
            "task": "app.workers.tasks.publish_due",
            "schedule": 60.0,
        },
    },
)

# Register tasks (import after app is defined to avoid a circular import).
from app.workers import tasks  # noqa: E402,F401
