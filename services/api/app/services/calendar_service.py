"""AI content-calendar planning: recommends what to post, on which platform,
and when. Timing/platform come from heuristics (replaceable with learned analytics
in Phase 5); the per-slot idea comes from the AI CalendarModule."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AIRequest, TaskType
from app.ai.model_policy import select_model
from app.ai.router import AIRouter
from app.models.ai_usage import AiUsage
from app.models.business import Business
from app.models.content import ContentItem
from app.models.enums import UNLIMITED, Channel, ContentType
from app.models.social_account import SocialAccount
from app.services import content_service, scheduling_service
from app.services.content_service import AiQuotaExceeded, usage_this_month
from app.services.rag_service import build_business_context


class NoConnectedAccount(Exception):
    """No connected account matches the slot's channel to schedule onto."""
    def __init__(self, channel: str) -> None:
        self.channel = channel
        super().__init__(f"no connected account for {channel}")

# Heuristic "best time to post" per channel (local HH:MM). Phase 5 replaces these
# with per-business learned optima from engagement analytics.
BEST_TIMES: dict[str, str] = {
    Channel.INSTAGRAM.value: "11:00",
    Channel.FACEBOOK.value: "13:00",
    Channel.LINKEDIN.value: "09:00",
    Channel.X.value: "08:00",
    Channel.THREADS.value: "12:00",
    Channel.GOOGLE_BUSINESS.value: "10:00",
}
ROTATION = [Channel.INSTAGRAM, Channel.FACEBOOK, Channel.LINKEDIN, Channel.X, Channel.THREADS]

# (slot count, day spacing) per horizon. Bounded to keep AI calls predictable.
# "day" is a one-time burst: one unique post per platform, all scheduled today.
TIMEFRAMES: dict[str, tuple[int, int]] = {
    "day": (len(ROTATION), 0),
    "week": (3, 2),
    "month": (8, 3),
    "quarter": (8, 11),
    "year": (12, 30),
}

# Campaign cadence: (number of posting days, days between them). Every posting day
# hits ALL platforms at once, spaced every other day (spacing 2). Day counts are
# capped so a whole-campaign draft stays a bounded number of AI generations
# (days * len(ROTATION) posts) rather than exploding for longer horizons.
CAMPAIGN_CADENCE: dict[str, tuple[int, int]] = {
    "day": (1, 0),
    "week": (3, 2),
    "month": (6, 2),
    "quarter": (10, 3),
    "year": (14, 7),
}


def _check_quota(db: Session, business: Business) -> None:
    limit = business.plan.ai_monthly_quota if business.plan else UNLIMITED
    if limit != UNLIMITED and usage_this_month(db, business.id) >= limit:
        raise AiQuotaExceeded(limit)


def plan(
    db: Session, *, router: AIRouter, business: Business, timeframe: str,
    theme: str, start: date | None = None,
) -> dict:
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"unknown timeframe: {timeframe}")
    _check_quota(db, business)

    count, spacing = TIMEFRAMES[timeframe]
    start = start or date.today()
    context = build_business_context(business)

    slots = []
    for i in range(count):
        channel = ROTATION[i % len(ROTATION)]
        slot_date = start + timedelta(days=spacing * (i + 1))
        resp = router.handle(AIRequest(
            task=TaskType.CALENDAR,
            prompt=f"{theme} (idea {i + 1} of {count})",
            business_id=str(business.id),
            context={"business": context, "channel": channel.value, "timeframe": timeframe},
            model=select_model(task=TaskType.CALENDAR),
        ))
        db.add(AiUsage(
            business_id=business.id, module=TaskType.CALENDAR.value,
            provider=resp.provider, model=resp.model,
            input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
        ))
        slots.append({
            "date": slot_date.isoformat(),
            "channel": channel.value,
            "recommended_time": BEST_TIMES.get(channel.value, "10:00"),
            "topic": resp.text,
        })
    db.flush()
    return {"timeframe": timeframe, "slots": slots}


def campaign_plan(
    db: Session, *, router: AIRouter, business: Business, timeframe: str,
    theme: str, start: date | None = None, channels: list[Channel] | None = None,
) -> dict:
    """Plan a campaign that posts to every target platform on each posting day, with
    days spaced every other day. `channels` defaults to the full rotation; pass the
    business's connected platforms so the studio only generates for what's connected.
    One AI idea is generated per posting day and shared across the platforms (each
    channel gets its own tailored post downstream). Returns days * len(channels) slots."""
    if timeframe not in CAMPAIGN_CADENCE:
        raise ValueError(f"unknown timeframe: {timeframe}")
    _check_quota(db, business)

    targets = channels or ROTATION
    days, spacing = CAMPAIGN_CADENCE[timeframe]
    start = start or date.today()
    context = build_business_context(business)

    slots = []
    for d in range(days):
        slot_date = start + timedelta(days=spacing * d)
        resp = router.handle(AIRequest(
            task=TaskType.CALENDAR,
            prompt=f"{theme} (posting day {d + 1} of {days})",
            business_id=str(business.id),
            context={"business": context, "timeframe": timeframe},
            model=select_model(task=TaskType.CALENDAR),
        ))
        db.add(AiUsage(
            business_id=business.id, module=TaskType.CALENDAR.value,
            provider=resp.provider, model=resp.model,
            input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
        ))
        for channel in targets:
            slots.append({
                "date": slot_date.isoformat(),
                "channel": channel.value,
                "recommended_time": BEST_TIMES.get(channel.value, "10:00"),
                "topic": resp.text,
            })
    db.flush()
    return {"timeframe": timeframe, "slots": slots}


def schedule_slot(
    db: Session, *, router: AIRouter, business: Business,
    channel: Channel, content_type: ContentType, topic: str,
    scheduled_at: datetime, created_by: uuid.UUID | None,
    social_account_id: uuid.UUID | None = None,
) -> tuple[ContentItem, "scheduling_service.Schedule"]:
    """Bridge calendar → scheduling: generate a post from the slot topic and
    schedule it. The account is resolved from the channel unless one is given."""
    if social_account_id is not None:
        # Validated as tenant-owned by schedule_item below.
        account_id = social_account_id
    else:
        account = db.scalar(
            select(SocialAccount)
            .where(
                SocialAccount.business_id == business.id,
                SocialAccount.platform == channel.value,
            )
            .order_by(SocialAccount.created_at)
        )
        if account is None:
            raise NoConnectedAccount(channel.value)
        account_id = account.id

    # Generating first also enforces the AI quota (raises AiQuotaExceeded).
    item = content_service.generate_single(
        db, router=router, business=business,
        channel=channel, content_type=content_type, brief=topic, created_by=created_by,
    )
    schedule = scheduling_service.schedule_item(
        db, business_id=business.id, content_item_id=item.id,
        social_account_id=account_id, scheduled_at=scheduled_at,
    )
    return item, schedule
