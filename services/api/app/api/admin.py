"""Operator-only routes (cross-tenant). Gated to platform admins by email —
NOT tenant-scoped, so it must never use get_membership_ctx."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.models.user import User
from app.services import admin_service

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
