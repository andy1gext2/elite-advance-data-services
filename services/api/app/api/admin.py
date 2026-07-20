"""Operator-only routes (cross-tenant). Gated to platform admins by email —
NOT tenant-scoped, so it must never use get_membership_ctx."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.models.business import Business
from app.models.user import User
from app.services import admin_service, plan_service

router = APIRouter(prefix="/admin", tags=["admin"])


def require_platform_admin(user: User = Depends(get_current_user)) -> User:
    """Allow only configured platform-operator emails (PLATFORM_ADMIN_EMAILS)."""
    if user.email.lower() not in get_settings().admin_emails:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return user


@router.get("/usage")
def usage_costs(
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Per-tenant AI cost vs subscription revenue for the current month."""
    return admin_service.usage_costs(db)


class SetPlanIn(BaseModel):
    tier: str


@router.post("/businesses/{business_id}/plan")
def set_business_plan(
    business_id: uuid.UUID,
    body: SetPlanIn,
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Operator override: set a business's plan directly (no Stripe). Use for comp
    accounts, support, or stress-testing (Enterprise = unlimited quotas)."""
    plan = plan_service.get_plan_by_tier(db, body.tier)
    if not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown plan tier")
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    business.plan_id = plan.id
    db.commit()
    return {"business_id": str(business_id), "tier": plan.tier, "plan": plan.name}
