"""Scheduling use-cases + the publish engine.

`run_due` is a plain function that the Celery beat task (and the dev "run-due"
endpoint) call — so the publish loop is fully testable without a broker. All
operations are tenant-scoped by business.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.connectors.registry import get_connector
from app.core.crypto import decrypt, encrypt
from app.models.content import ContentItem
from app.models.enums import ContentStatus, Platform, ScheduleStatus
from app.models.publish_job import PublishJob
from app.models.schedule import Schedule
from app.models.social_account import SocialAccount

MAX_ATTEMPTS = 3


class NotFound(Exception):
    ...


class InvalidSchedule(Exception):
    ...


def _to_naive_utc(dt: datetime) -> datetime:
    """Normalize to naive UTC for storage + reliable comparisons across backends."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Accounts ────────────────────────────────────────
def connect_account(
    db: Session, *, business_id: uuid.UUID, platform: Platform,
    display_name: str, access_token: str = "mock-token", external_id: str | None = None,
) -> SocialAccount:
    """Store a connected account. Real OAuth lands in the connector layer; for now
    the token is provided directly and encrypted at rest."""
    account = SocialAccount(
        business_id=business_id,
        platform=platform.value,
        display_name=display_name,
        external_id=external_id,
        access_token_enc=encrypt(access_token),
        status="connected",
    )
    db.add(account)
    db.flush()
    return account


def upsert_oauth_account(
    db: Session, *, business_id: uuid.UUID, platform: str, access_token: str,
    external_id: str | None = None, display_name: str | None = None,
    expires_at: datetime | None = None,
) -> SocialAccount:
    """Store (or refresh) a connected account after an OAuth exchange. One account
    per (business, platform) — re-authing updates the encrypted token in place."""
    account = db.scalar(
        select(SocialAccount).where(
            SocialAccount.business_id == business_id,
            SocialAccount.platform == platform,
        )
    )
    if account is None:
        account = SocialAccount(business_id=business_id, platform=platform)
        db.add(account)
    account.access_token_enc = encrypt(access_token)
    if external_id:
        account.external_id = external_id
    if display_name:
        account.display_name = display_name
    account.status = "connected"
    account.expires_at = expires_at
    db.flush()
    return account


def list_accounts(db: Session, *, business_id: uuid.UUID) -> list[SocialAccount]:
    return list(db.scalars(
        select(SocialAccount).where(SocialAccount.business_id == business_id)
        .order_by(SocialAccount.created_at)
    ).all())


# ── Scheduling ──────────────────────────────────────
def _load_scoped(db: Session, model, business_id: uuid.UUID, obj_id: uuid.UUID):
    obj = db.get(model, obj_id)
    if not obj or obj.business_id != business_id:
        raise NotFound(f"{model.__name__} {obj_id}")
    return obj


def schedule_item(
    db: Session, *, business_id: uuid.UUID, content_item_id: uuid.UUID,
    social_account_id: uuid.UUID, scheduled_at: datetime,
    repost_interval_days: int | None = None,
) -> Schedule:
    # Validate both belong to the tenant (raises NotFound otherwise).
    _load_scoped(db, ContentItem, business_id, content_item_id)
    _load_scoped(db, SocialAccount, business_id, social_account_id)
    if repost_interval_days is not None and repost_interval_days <= 0:
        raise InvalidSchedule("repost_interval_days must be positive")

    schedule = Schedule(
        business_id=business_id,
        content_item_id=content_item_id,
        social_account_id=social_account_id,
        scheduled_at=_to_naive_utc(scheduled_at),
        status=ScheduleStatus.PENDING.value,
        repost_interval_days=repost_interval_days,
    )
    db.add(schedule)
    db.flush()
    return schedule


def bulk_schedule(db: Session, *, business_id: uuid.UUID, items: list[dict]) -> list[Schedule]:
    return [
        schedule_item(
            db, business_id=business_id,
            content_item_id=i["content_item_id"],
            social_account_id=i["social_account_id"],
            scheduled_at=i["scheduled_at"],
            repost_interval_days=i.get("repost_interval_days"),
        )
        for i in items
    ]


def list_schedules(
    db: Session, *, business_id: uuid.UUID,
    start: datetime | None = None, end: datetime | None = None, status: str | None = None,
) -> list[Schedule]:
    stmt = select(Schedule).where(Schedule.business_id == business_id)
    if start:
        stmt = stmt.where(Schedule.scheduled_at >= _to_naive_utc(start))
    if end:
        stmt = stmt.where(Schedule.scheduled_at <= _to_naive_utc(end))
    if status:
        stmt = stmt.where(Schedule.status == status)
    return list(db.scalars(stmt.order_by(Schedule.scheduled_at)).all())


def cancel(db: Session, *, business_id: uuid.UUID, schedule_id: uuid.UUID) -> Schedule:
    schedule = _load_scoped(db, Schedule, business_id, schedule_id)
    if schedule.status in (ScheduleStatus.PUBLISHED.value, ScheduleStatus.PUBLISHING.value):
        raise InvalidSchedule(f"cannot cancel a {schedule.status} schedule")
    schedule.status = ScheduleStatus.CANCELED.value
    db.flush()
    return schedule


# ── Publish engine (called by Celery beat + the dev run-due endpoint) ──
def run_due(
    db: Session, *, now: datetime | None = None, business_id: uuid.UUID | None = None,
) -> dict:
    """Publish every PENDING schedule whose time has arrived. Returns a summary.

    Idempotent per row via a PENDING→PUBLISHING flip; writes a PublishJob for each
    attempt; on success reschedules a repost if configured."""
    now = _to_naive_utc(now) if now else _utcnow()
    conds = [Schedule.status == ScheduleStatus.PENDING.value, Schedule.scheduled_at <= now]
    if business_id is not None:
        conds.append(Schedule.business_id == business_id)
    due = list(db.scalars(select(Schedule).where(and_(*conds))).all())

    published = failed = 0
    for schedule in due:
        schedule.status = ScheduleStatus.PUBLISHING.value
        schedule.attempts += 1
        db.flush()

        item = db.get(ContentItem, schedule.content_item_id)
        account = db.get(SocialAccount, schedule.social_account_id)
        connector = get_connector(account.platform)
        token = decrypt(account.access_token_enc) if account.access_token_enc else ""

        result = connector.publish(
            account_token=token, body=item.body if item else "",
            meta=(item.meta if item else {}),
        )

        db.add(PublishJob(
            business_id=schedule.business_id,
            schedule_id=schedule.id,
            content_item_id=schedule.content_item_id,
            social_account_id=schedule.social_account_id,
            status="published" if result.ok else "failed",
            external_post_id=result.external_id,
            error=result.error,
        ))

        if result.ok:
            published += 1
            schedule.status = ScheduleStatus.PUBLISHED.value
            if item:
                item.status = ContentStatus.PUBLISHED.value
            if schedule.repost_interval_days:
                db.add(Schedule(
                    business_id=schedule.business_id,
                    content_item_id=schedule.content_item_id,
                    social_account_id=schedule.social_account_id,
                    scheduled_at=schedule.scheduled_at + timedelta(days=schedule.repost_interval_days),
                    status=ScheduleStatus.PENDING.value,
                    repost_interval_days=schedule.repost_interval_days,
                ))
        else:
            failed += 1
            # Retry until MAX_ATTEMPTS, then give up.
            schedule.status = (
                ScheduleStatus.PENDING.value
                if schedule.attempts < MAX_ATTEMPTS
                else ScheduleStatus.FAILED.value
            )
        db.flush()

    return {"due": len(due), "published": published, "failed": failed}
