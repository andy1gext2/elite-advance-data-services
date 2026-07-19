"""Async video generation: kick off a render, persist a VideoJob, and poll it
until the clip is ready — then store the bytes and stamp the content item's
video_url. Provider- and storage-agnostic (mirrors image_service, plus polling)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.base import AIRequest, TaskType
from app.ai.model_policy import select_model
from app.ai.router import AIRouter
from app.models.ai_usage import AiUsage
from app.models.asset import Asset
from app.models.business import Business
from app.models.content import ContentItem
from app.models.enums import UNLIMITED
from app.models.video_job import VideoJob
from app.services.content_service import (
    AiQuotaExceeded,
    usage_this_month as ai_usage_this_month,
)
from app.services.rag_service import build_business_context
from app.storage.base import Storage
from app.video.base import VideoProvider

# Vertical clips for feed platforms; landscape elsewhere.
_VERTICAL_CHANNELS = {"instagram", "threads", "video"}

# Claude turns a post's marketing message into a Veo shot brief. Constrained to an
# 8-second, single continuous shot so Veo produces a coherent clip.
_SCRIPT_SYSTEM = (
    "You are a creative director writing the shot brief for an 8-SECOND AI-generated "
    "marketing video (Google Veo). Turn the marketing message into ONE vivid, cinematic "
    "prompt Veo can execute as a single continuous ~8-second shot. Describe: the subject, "
    "ONE clear motion or action that begins and resolves within 8 seconds, camera movement, "
    "lighting, mood, setting, and visual style. Be concrete and sensory. Do NOT use "
    "timestamps, shot lists, spoken dialogue, or on-screen text/captions. Match the brand's "
    "vibe. Output ONLY the prompt, 2–4 sentences."
)


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
        "credits": business.video_credits,
    }


def _consume_allowance(db: Session, business: Business) -> None:
    """Allow a render if within the monthly quota; otherwise spend a paid credit.
    Raises VideoQuotaExceeded when both the monthly quota and credits are exhausted."""
    limit = business.plan.video_monthly_quota if business.plan else UNLIMITED
    if limit == UNLIMITED:
        return
    if usage_this_month(db, business.id) < limit:
        return  # within the plan's monthly allowance
    if business.video_credits > 0:
        business.video_credits -= 1  # overflow: spend a credit
        db.flush()
        return
    raise VideoQuotaExceeded(limit)


def add_credits(db: Session, business: Business, quantity: int) -> int:
    """Add paid render credits to a business (the billing webhook / purchase hook)."""
    business.video_credits = max(0, business.video_credits + quantity)
    db.flush()
    return business.video_credits


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


def generate_script(
    db: Session, *, router: AIRouter, business: Business, item: ContentItem
) -> str:
    """Claude turns the post's marketing message into an 8-second Veo shot brief — the
    creative vision Veo then executes. Grounds on brand + the promoted product.

    This is a real (billable) Claude call and is exposed as its own endpoint, so it
    must respect the tenant's monthly AI text quota — otherwise it's an ungated cost
    leak (the "Write vision" button could be spammed past the plan limit)."""
    limit = business.plan.ai_monthly_quota if business.plan else UNLIMITED
    if limit != UNLIMITED and ai_usage_this_month(db, business.id) >= limit:
        raise AiQuotaExceeded(limit)

    lines = [f"Brand: {business.name}."]
    if business.industry:
        lines.append(f"Industry: {business.industry}.")
    if business.tone:
        lines.append(f"Tone/mood: {business.tone}.")
    if business.brand_voice:
        lines.append(f"Brand character: {business.brand_voice}.")
    if item.product_asset_id:
        product = db.get(Asset, item.product_asset_id)
        if product:
            label = product.name or product.filename
            note = f" {product.description}" if product.description else ""
            lines.append(f"Feature this product prominently, true to life: {label}.{note}")

    concept = "\n".join(p for p in (item.title, item.body) if p).strip()
    prompt = "\n".join(lines) + f"\n\nMarketing message / post:\n{concept}\n\nWrite the 8-second Veo video prompt."

    resp = router.handle(AIRequest(
        task=TaskType.VIDEO_SCRIPT,
        prompt=prompt,
        business_id=str(business.id),
        context={"business": build_business_context(business)},
        system=_SCRIPT_SYSTEM,
        model=select_model(task=TaskType.VIDEO_SCRIPT),
        max_tokens=400,
        temperature=0.8,
    ))
    db.add(AiUsage(
        business_id=business.id, module="video_script",
        provider=resp.provider, model=resp.model,
        input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
    ))
    return resp.text.strip()


def start_video(
    db: Session, *, provider: VideoProvider, router: AIRouter,
    business: Business, item: ContentItem, script: str | None = None,
) -> VideoJob:
    """Kick off a render and record the job (status 'processing'). Enforces the
    tenant's monthly video quota + credits (raises VideoQuotaExceeded). Uses the
    provided `script` (an owner-edited vision) if given; otherwise Claude writes the
    8-second shot brief (falls back to a plain prompt on error). Veo executes it."""
    _consume_allowance(db, business)
    if script and script.strip():
        prompt = script.strip()
    else:
        try:
            prompt = generate_script(db, router=router, business=business, item=item)
        except Exception:  # noqa: BLE001 - never fail the render because scripting hiccuped
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
