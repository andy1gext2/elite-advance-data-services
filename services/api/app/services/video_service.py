"""Async video generation: kick off a render, persist a VideoJob, and poll it
until the clip is ready — then store the bytes and stamp the content item's
video_url. Provider- and storage-agnostic (mirrors image_service, plus polling)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.content import ContentItem
from app.models.enums import UNLIMITED
from app.models.video_job import VideoJob
from app.storage.base import Storage
from app.video.base import VideoProvider

# Vertical clips for feed platforms; landscape elsewhere.
_VERTICAL_CHANNELS = {"instagram", "threads", "video"}


class VideoQuotaExceeded(Exception):
    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"monthly video quota ({limit}) reached")


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def usage_this_month(db: Session, business_id: uuid.UUID) -> int:
    """Video renders started this month (each start counts, since each is billable)."""
    return db.scalar(
        select(func.count(VideoJob.id)).where(
            VideoJob.business_id == business_id,
            VideoJob.created_at >= _month_start(),
        )
    ) or 0


def quota(db: Session, business: Business) -> dict:
    limit = business.plan.video_monthly_quota if business.plan else UNLIMITED
    used = usage_this_month(db, business.id)
    unlimited = limit == UNLIMITED
    return {
        "used": used,
        "limit": None if unlimited else limit,
        "remaining": None if unlimited else max(0, limit - used),
        "unlimited": unlimited,
    }


def _check_quota(db: Session, business: Business) -> None:
    limit = business.plan.video_monthly_quota if business.plan else UNLIMITED
    if limit != UNLIMITED and usage_this_month(db, business.id) >= limit:
        raise VideoQuotaExceeded(limit)


def build_prompt(business: Business, item: ContentItem) -> str:
    first_line = (item.body or "").strip().splitlines()[0][:220] if item.body else ""
    parts = [f"Short marketing video for {business.name}."]
    if business.industry:
        parts.append(f"Industry: {business.industry}.")
    if business.tone:
        parts.append(f"Mood: {business.tone}.")
    if business.brand_voice:
        parts.append(f"Brand character: {business.brand_voice}.")
    if first_line:
        parts.append(f"Concept: {first_line}")
    parts.append(
        "Cinematic, smooth camera motion, high-quality, on-brand, natural lighting, "
        "no text or logos overlaid. Keep a consistent look with the brand's approved posts."
    )
    return " ".join(parts)


def start_video(
    db: Session, *, provider: VideoProvider, business: Business, item: ContentItem
) -> VideoJob:
    """Kick off a render and record the job (status 'processing'). Enforces the
    tenant's monthly video quota (raises VideoQuotaExceeded)."""
    _check_quota(db, business)
    prompt = build_prompt(business, item)
    aspect = "9:16" if item.channel in _VERTICAL_CHANNELS else "16:9"
    operation_ref = provider.start(prompt=prompt, aspect=aspect)
    job = VideoJob(
        business_id=item.business_id,
        content_item_id=item.id,
        status="processing",
        provider=provider.name,
        model=provider.model,
        prompt=prompt,
        operation_ref=operation_ref,
    )
    db.add(job)
    db.flush()
    return job


def latest_job(db: Session, *, business_id: uuid.UUID, content_item_id: uuid.UUID) -> VideoJob | None:
    return db.scalar(
        select(VideoJob)
        .where(
            VideoJob.business_id == business_id,
            VideoJob.content_item_id == content_item_id,
        )
        .order_by(VideoJob.created_at.desc())
    )


def poll_video(
    db: Session, *, provider: VideoProvider, storage: Storage, job: VideoJob
) -> VideoJob:
    """Advance a processing job: check the provider; on success store the clip and
    set the content item's video_url. No-op for already-finished jobs."""
    if job.status != "processing":
        return job

    result = provider.poll(job.operation_ref)
    if result.status == "processing":
        return job
    if result.status == "failed" or not result.data:
        job.status = "failed"
        job.error = result.error or "generation failed"
        db.flush()
        return job

    key = f"content/{job.business_id}/{uuid.uuid4().hex}.mp4"
    url = storage.save(key=key, data=result.data, content_type=result.mime or "video/mp4")
    job.video_url = url
    job.status = "succeeded"
    item = db.get(ContentItem, job.content_item_id)
    if item is not None:
        item.video_url = url
    db.flush()
    return job


def advance_processing_jobs(
    db: Session, *, provider: VideoProvider, storage: Storage, limit: int = 25
) -> dict:
    """Poll all in-flight jobs across tenants and advance any that have finished.
    Called by the Celery beat task so renders complete without the browser polling."""
    jobs = list(db.scalars(
        select(VideoJob).where(VideoJob.status == "processing")
        .order_by(VideoJob.created_at).limit(limit)
    ).all())
    done = failed = 0
    for job in jobs:
        poll_video(db, provider=provider, storage=storage, job=job)
        if job.status == "succeeded":
            done += 1
        elif job.status == "failed":
            failed += 1
    return {"checked": len(jobs), "succeeded": done, "failed": failed}
