"""Operator (cross-tenant) analytics: per-business AI cost vs subscription revenue.

Not tenant-scoped — this aggregates over every business, so it is gated to platform
admins at the API layer (see api/admin.py). Text cost is exact (from stored token
counts); image/video are per-asset estimates from Settings.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.pricing import text_cost_usd
from app.models.ai_usage import AiUsage
from app.models.business import Business
from app.models.plan import Plan
from app.models.video_job import VideoJob

IMAGE_MODULE = "image"


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def usage_costs(db: Session) -> dict:
    """Per-business cost breakdown for the current month, plus platform totals."""
    settings = get_settings()
    since = _month_start()

    plans = {p.id: p for p in db.scalars(select(Plan)).all()}
    businesses = list(db.scalars(select(Business).order_by(Business.created_at)).all())

    # Seed a row per business so tenants with zero usage still appear.
    rows: dict = {
        b.id: {
            "business_id": str(b.id),
            "name": b.name,
            "plan": (plans[b.plan_id].name if b.plan_id in plans else None),
            "tier": (plans[b.plan_id].tier if b.plan_id in plans else None),
            # Advertised subscription price is stored in cents.
            "mrr_usd": round((plans[b.plan_id].price_monthly / 100), 2) if b.plan_id in plans else 0.0,
            "text_generations": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "text_cost_usd": 0.0,
            "images": 0,
            "videos": 0,
        }
        for b in businesses
    }

    # Text + image usage from the AiUsage ledger (this month). Priced per row so
    # mixed models (Opus vs Haiku) cost correctly.
    for u in db.scalars(select(AiUsage).where(AiUsage.created_at >= since)).all():
        r = rows.get(u.business_id)
        if r is None:
            continue
        if u.module == IMAGE_MODULE:
            r["images"] += 1
        else:
            r["text_generations"] += 1
            r["input_tokens"] += u.input_tokens
            r["output_tokens"] += u.output_tokens
            r["text_cost_usd"] += text_cost_usd(u.model, u.input_tokens, u.output_tokens)

    # Video renders (this month) — counted from VideoJob, one row per render.
    for business_id, count in db.execute(
        select(VideoJob.business_id, func.count(VideoJob.id))
        .where(VideoJob.created_at >= since)
        .group_by(VideoJob.business_id)
    ).all():
        r = rows.get(business_id)
        if r is not None:
            r["videos"] = count

    out: list[dict] = []
    for r in rows.values():
        image_cost = r["images"] * settings.cost_per_image_usd
        video_cost = r["videos"] * settings.cost_per_video_usd
        total = r["text_cost_usd"] + image_cost + video_cost
        r["image_cost_usd"] = round(image_cost, 2)
        r["video_cost_usd"] = round(video_cost, 2)
        r["text_cost_usd"] = round(r["text_cost_usd"], 4)
        r["total_cost_usd"] = round(total, 2)
        r["margin_usd"] = round(r["mrr_usd"] - total, 2)
        out.append(r)

    # Highest cost first — the tenants to watch.
    out.sort(key=lambda r: r["total_cost_usd"], reverse=True)

    totals = {
        "businesses": len(out),
        "mrr_usd": round(sum(r["mrr_usd"] for r in out), 2),
        "total_cost_usd": round(sum(r["total_cost_usd"] for r in out), 2),
        "margin_usd": round(sum(r["margin_usd"] for r in out), 2),
    }
    return {"period_start": since.isoformat(), "totals": totals, "businesses": out}
