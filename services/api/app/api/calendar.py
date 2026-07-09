"""AI content-calendar routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.registry import get_ai_router
from app.ai.router import AIRouter
from app.api.deps import TenantContext, require_role
from app.core.db import get_db
from app.models.enums import Role
from app.schemas.calendar import PlanIn, PlanOut, ScheduleSlotIn, ScheduleSlotOut
from app.services import calendar_service, scheduling_service
from app.services.content_service import AiQuotaExceeded

router = APIRouter(prefix="/businesses/{business_id}/calendar", tags=["calendar"])


@router.post("/plan", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def plan(
    body: PlanIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> PlanOut:
    try:
        result = calendar_service.plan(
            db, router=ai, business=ctx.business, timeframe=body.timeframe, theme=body.theme
        )
    except AiQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly AI quota ({exc.limit}) reached. Upgrade to plan more.",
        )
    db.commit()
    return result


@router.post("/schedule-slot", response_model=ScheduleSlotOut, status_code=status.HTTP_201_CREATED)
def schedule_slot(
    body: ScheduleSlotIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> ScheduleSlotOut:
    try:
        item, schedule = calendar_service.schedule_slot(
            db, router=ai, business=ctx.business,
            channel=body.channel, content_type=body.content_type,
            topic=body.topic, scheduled_at=body.scheduled_at,
            social_account_id=body.social_account_id,
            created_by=ctx.membership.user_id,
        )
    except calendar_service.NoConnectedAccount as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connect a {exc.channel} account to schedule this slot.",
        )
    except scheduling_service.NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    except AiQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly AI quota ({exc.limit}) reached. Upgrade to schedule more.",
        )
    db.commit()
    db.refresh(item)
    db.refresh(schedule)
    return ScheduleSlotOut(content_item=item, schedule=schedule)
