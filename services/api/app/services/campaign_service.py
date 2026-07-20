"""Campaigns + autopilot (approve-first).

`propose` drafts a whole campaign — an AI calendar plan, one generated content item
per slot, and a matching connected account — and parks it as PROPOSED. A human
`approve`s it, which turns each item into a real Schedule (the publish engine then
posts them when due). `run_autopilot` proposes campaigns on each tenant's cadence so
they're waiting for approval automatically. Nothing publishes without human sign-off."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.router import AIRouter
from app.models.asset import Asset
from app.models.business import Business
from app.models.campaign import Campaign, CampaignItem
from app.models.content import ContentItem
from app.models.enums import (
    CampaignSource,
    CampaignStatus,
    Channel,
    ContentType,
    Platform,
    ScheduleStatus,
)
from app.models.social_account import SocialAccount
from app.services import calendar_service, content_service, scheduling_service

# A social channel a mock/real account can publish to (subset of Channel).
_PLATFORM_CHANNELS = {p.value for p in Platform}

# Which social channels the studio can generate for, in priority order.
_SOCIAL_CHANNELS = [
    Channel.INSTAGRAM, Channel.FACEBOOK, Channel.LINKEDIN,
    Channel.X, Channel.THREADS, Channel.GOOGLE_BUSINESS,
]


def _connected_channels(db: Session, business_id: uuid.UUID) -> list[Channel]:
    """The social channels this business has connected accounts for — the studio
    generates only for these. Empty if none are connected (caller falls back to all)."""
    connected = {
        a.platform for a in scheduling_service.list_accounts(db, business_id=business_id)
    }
    return [c for c in _SOCIAL_CHANNELS if c.value in connected]


class CampaignNotFound(Exception):
    ...


class CampaignItemNotFound(Exception):
    ...


class InvalidCampaignState(Exception):
    ...


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _slot_datetime(date_str: str, time_str: str) -> datetime:
    """Combine a plan slot's date + recommended HH:MM into a naive datetime."""
    try:
        return datetime.fromisoformat(f"{date_str}T{time_str}:00")
    except ValueError:
        return datetime.fromisoformat(f"{date_str}T10:00:00")


def _account_for(db: Session, business_id: uuid.UUID, channel: str) -> SocialAccount | None:
    if channel not in _PLATFORM_CHANNELS:
        return None
    return db.scalar(
        select(SocialAccount)
        .where(SocialAccount.business_id == business_id, SocialAccount.platform == channel)
        .order_by(SocialAccount.created_at)
    )


def _product_note(product: Asset | None) -> str:
    """A short instruction that grounds the campaign in the promoted product —
    the 'navigator' the AI writes toward."""
    if product is None:
        return ""
    label = product.name or product.filename
    note = f" Promote this product: {label}."
    if product.description:
        note += f" {product.description}"
    return note


def propose(
    db: Session, *, router: AIRouter, business: Business, theme: str,
    timeframe: str = "week", source: CampaignSource = CampaignSource.MANUAL,
    created_by: uuid.UUID | None = None, product: Asset | None = None,
    start: date | None = None,
) -> Campaign:
    """Draft a full campaign for approval: plan -> generate content per slot ->
    resolve accounts. When a product is given, its name + description steer both the
    plan and each post. Consumes AI quota (raises AiQuotaExceeded, possibly mid-run)."""
    note = _product_note(product)
    # Generate only for the platforms this business has connected (all, if none yet).
    targets = _connected_channels(db, business.id)
    # Every posting day hits all target platforms at once (spaced every other day).
    plan = calendar_service.campaign_plan(
        db, router=router, business=business, timeframe=timeframe,
        theme=f"{theme}.{note}" if note else theme,
        channels=targets or None, start=start,
    )

    campaign = Campaign(
        business_id=business.id,
        name=theme[:255],
        timeframe=timeframe,
        product_asset_id=product.id if product else None,
        status=CampaignStatus.PROPOSED.value,
        source=source.value,
        created_by=created_by,
    )
    db.add(campaign)
    db.flush()

    for slot in plan["slots"]:
        channel = slot["channel"]
        # generate_single enforces the AI quota; stop cleanly if it's exhausted.
        try:
            item = content_service.generate_single(
                db, router=router, business=business,
                channel=Channel(channel), content_type=ContentType.SOCIAL_POST,
                brief=f"{slot['topic']}{note}", created_by=created_by,
            )
        except content_service.AiQuotaExceeded:
            break
        if product is not None:
            item.product_asset_id = product.id  # so its image auto-grounds on the product
            # For a service with an AI flyer already made, reuse that EXACT image on
            # every platform's post (copy-paste), rather than a per-post render.
            if product.is_service and product.url:
                item.image_url = product.url
                item.image_prompt = "Reused service flyer"
            db.flush()
        account = _account_for(db, business.id, channel)
        db.add(CampaignItem(
            campaign_id=campaign.id,
            business_id=business.id,
            content_item_id=item.id,
            social_account_id=account.id if account else None,
            channel=channel,
            scheduled_at=_slot_datetime(slot["date"], slot["recommended_time"]),
            status="proposed",
        ))
    db.flush()
    return campaign


def get(db: Session, *, business_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign:
    c = db.scalar(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.business_id == business_id)
    )
    if not c:
        raise CampaignNotFound(str(campaign_id))
    return c


def list_campaigns(
    db: Session, *, business_id: uuid.UUID, status: str | None = None
) -> list[Campaign]:
    stmt = select(Campaign).where(Campaign.business_id == business_id)
    if status:
        stmt = stmt.where(Campaign.status == status)
    return list(db.scalars(stmt.order_by(Campaign.created_at.desc())).all())


def calendar_items(db: Session, *, business_id: uuid.UUID) -> list[dict]:
    """Flatten every campaign's posts into dated calendar entries (bird's-eye view).
    Skips rejected campaigns. Joined with content copy + campaign name for display."""
    rows = db.execute(
        select(CampaignItem, Campaign.name, ContentItem.title, ContentItem.body)
        .join(Campaign, CampaignItem.campaign_id == Campaign.id)
        .outerjoin(ContentItem, CampaignItem.content_item_id == ContentItem.id)
        .where(
            CampaignItem.business_id == business_id,
            Campaign.status != CampaignStatus.REJECTED.value,
        )
        .order_by(CampaignItem.scheduled_at)
    ).all()
    return [
        {
            "id": item.id,
            "campaign_id": item.campaign_id,
            "campaign_name": campaign_name,
            "channel": item.channel,
            "scheduled_at": item.scheduled_at,
            "status": item.status,
            "content_item_id": item.content_item_id,
            "title": title,
            "body": body,
        }
        for item, campaign_name, title, body in rows
    ]


def reschedule_item(
    db: Session, *, business_id: uuid.UUID, item_id: uuid.UUID, new_date: date
) -> dict:
    """Move a calendar post to a different day (drag-and-drop). Keeps its time of
    day, and moves the linked publish Schedule too so the post actually goes out on
    the new date. Published posts can't be moved."""
    from app.models.schedule import Schedule

    item = db.scalar(
        select(CampaignItem).where(
            CampaignItem.id == item_id, CampaignItem.business_id == business_id
        )
    )
    if not item:
        raise CampaignItemNotFound(str(item_id))
    if item.status == "published":
        raise CampaignItemNotFound(str(item_id))  # not movable once published

    item.scheduled_at = datetime.combine(new_date, item.scheduled_at.time())

    # If this post has a real publish schedule (approved + connected account),
    # move it to match so it publishes on the new date.
    if item.content_item_id:
        sched = db.scalar(
            select(Schedule).where(
                Schedule.business_id == business_id,
                Schedule.content_item_id == item.content_item_id,
            )
        )
        if sched is not None:
            sched.scheduled_at = datetime.combine(new_date, sched.scheduled_at.time())

    db.flush()
    return {"id": str(item.id), "scheduled_at": item.scheduled_at.isoformat()}


def approve(db: Session, *, business_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign:
    """Schedule every item that has a connected account; skip the rest. The publish
    engine takes it from here."""
    campaign = get(db, business_id=business_id, campaign_id=campaign_id)
    if campaign.status != CampaignStatus.PROPOSED.value:
        raise InvalidCampaignState(f"campaign is {campaign.status}, not proposed")

    for item in campaign.items:
        if item.social_account_id and item.content_item_id:
            scheduling_service.schedule_item(
                db, business_id=business_id,
                content_item_id=item.content_item_id,
                social_account_id=item.social_account_id,
                scheduled_at=item.scheduled_at,
            )
            item.status = "scheduled"
            content = db.get(ContentItem, item.content_item_id)
            if content:
                content.status = "approved"
        else:
            item.status = "skipped"  # no connected account for this channel

    campaign.status = CampaignStatus.SCHEDULED.value
    db.flush()
    return campaign


def reject(db: Session, *, business_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign:
    campaign = get(db, business_id=business_id, campaign_id=campaign_id)
    if campaign.status != CampaignStatus.PROPOSED.value:
        raise InvalidCampaignState(f"campaign is {campaign.status}, not proposed")
    campaign.status = CampaignStatus.REJECTED.value
    db.flush()
    return campaign


# ── Autopilot (cadence) ─────────────────────────────
def run_autopilot(db: Session, *, router: AIRouter, now: datetime | None = None) -> dict:
    """Propose a campaign for every autopilot-enabled tenant whose cadence is due.
    Called by the Celery beat task. Proposals wait for human approval."""
    now = now or _utcnow()
    due = list(db.scalars(
        select(Business).where(Business.autopilot_enabled.is_(True))
    ).all())

    proposed = 0
    for business in due:
        last = business.autopilot_last_run_at
        if last is not None:
            last_naive = last.replace(tzinfo=None) if last.tzinfo else last
            if now - last_naive < timedelta(days=business.autopilot_frequency_days):
                continue
        theme = business.autopilot_theme or business.goals or "Grow our brand and engage our audience"
        try:
            propose(
                db, router=router, business=business, theme=theme,
                timeframe=business.autopilot_timeframe,
                source=CampaignSource.AUTOPILOT,
            )
        except content_service.AiQuotaExceeded:
            continue
        business.autopilot_last_run_at = now
        proposed += 1
    db.flush()
    return {"eligible": len(due), "proposed": proposed}
