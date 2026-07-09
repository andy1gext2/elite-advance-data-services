"""Analytics dashboard + AI business insights. Tenant-scoped.
Dashboard is read (membership); insights generation is editor+ (AI cost)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.registry import get_ai_router
from app.ai.router import AIRouter
from app.api.deps import TenantContext, get_membership_ctx, require_role
from app.core.db import get_db
from app.models.enums import Role
from app.schemas.analytics import DashboardOut, InsightsOut
from app.services import analytics_service
from app.services.content_service import AiQuotaExceeded

router = APIRouter(prefix="/businesses/{business_id}", tags=["analytics"])


@router.get("/analytics/dashboard", response_model=DashboardOut)
def dashboard(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> DashboardOut:
    return DashboardOut(**analytics_service.dashboard(db, business_id=ctx.business.id))


@router.post("/insights/generate", response_model=InsightsOut)
def generate_insights(
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> InsightsOut:
    try:
        result = analytics_service.generate_insights(db, router=ai, business=ctx.business)
    except AiQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly AI quota ({exc.limit}) reached. Upgrade for more insights.",
        )
    db.commit()
    return InsightsOut(**result)
