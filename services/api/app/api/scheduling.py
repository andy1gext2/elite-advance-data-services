"""Integrations (connected accounts) + scheduling routes. Tenant-scoped."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_membership_ctx, require_role
from app.core.db import get_db
from app.models.enums import Role
from app.schemas.scheduling import (
    BulkScheduleIn,
    ConnectAccountIn,
    RescheduleIn,
    RunDueOut,
    ScheduleIn,
    ScheduleOut,
    SocialAccountOut,
)
from app.services import scheduling_service

router = APIRouter(prefix="/businesses/{business_id}", tags=["scheduling"])


def _account_out(account) -> SocialAccountOut:
    return SocialAccountOut(
        id=account.id, platform=account.platform, display_name=account.display_name,
        external_id=account.external_id, status=account.status,
        **scheduling_service.account_status(account),
    )


# ── Integrations / accounts ─────────────────────────
@router.post("/integrations/accounts", response_model=SocialAccountOut, status_code=status.HTTP_201_CREATED)
def connect_account(
    body: ConnectAccountIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> SocialAccountOut:
    account = scheduling_service.connect_account(
        db, business_id=ctx.business.id, platform=body.platform,
        display_name=body.display_name, external_id=body.external_id,
    )
    db.commit()
    db.refresh(account)
    return _account_out(account)


@router.get("/integrations/accounts", response_model=list[SocialAccountOut])
def list_accounts(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> list[SocialAccountOut]:
    return [
        _account_out(a)
        for a in scheduling_service.list_accounts(db, business_id=ctx.business.id)
    ]


# ── Schedules ───────────────────────────────────────
def _schedule(db: Session, business_id: uuid.UUID, body: ScheduleIn):
    try:
        return scheduling_service.schedule_item(
            db, business_id=business_id,
            content_item_id=body.content_item_id,
            social_account_id=body.social_account_id,
            scheduled_at=body.scheduled_at,
            repost_interval_days=body.repost_interval_days,
        )
    except scheduling_service.NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item or account not found")
    except scheduling_service.InvalidSchedule as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/schedules", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    body: ScheduleIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ScheduleOut:
    schedule = _schedule(db, ctx.business.id, body)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.post("/schedules/bulk", response_model=list[ScheduleOut], status_code=status.HTTP_201_CREATED)
def bulk_schedule(
    body: BulkScheduleIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> list[ScheduleOut]:
    schedules = [_schedule(db, ctx.business.id, item) for item in body.items]
    db.commit()
    for s in schedules:
        db.refresh(s)
    return schedules


@router.get("/schedules", response_model=list[ScheduleOut])
def list_schedules(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[ScheduleOut]:
    return scheduling_service.list_schedules(
        db, business_id=ctx.business.id, start=start, end=end, status=status_filter
    )


@router.patch("/schedules/{schedule_id}", response_model=ScheduleOut)
def reschedule_schedule(
    schedule_id: uuid.UUID,
    body: RescheduleIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ScheduleOut:
    try:
        schedule = scheduling_service.reschedule(
            db, business_id=ctx.business.id, schedule_id=schedule_id,
            scheduled_at=body.scheduled_at, social_account_id=body.social_account_id,
        )
    except scheduling_service.NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule or account not found")
    except scheduling_service.InvalidSchedule as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    db.commit()
    db.refresh(schedule)
    return schedule


@router.post("/schedules/{schedule_id}/cancel", response_model=ScheduleOut)
def cancel_schedule(
    schedule_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ScheduleOut:
    try:
        schedule = scheduling_service.cancel(db, business_id=ctx.business.id, schedule_id=schedule_id)
    except scheduling_service.NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    except scheduling_service.InvalidSchedule as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    db.commit()
    db.refresh(schedule)
    return schedule


@router.post("/schedules/run-due", response_model=RunDueOut)
def run_due(
    ctx: TenantContext = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> RunDueOut:
    """Manual/dev trigger for the publish engine (stands in for the Celery beat).
    Publishes this tenant's schedules whose time has arrived."""
    summary = scheduling_service.run_due(db, business_id=ctx.business.id)
    db.commit()
    return RunDueOut(**summary)
