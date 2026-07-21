"""Industry trends: the curated industry list (public, for the onboarding
combobox) + a tenant's cached trend brief for the dashboard suggestions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.registry import get_ai_router
from app.ai.router import AIRouter
from app.api.deps import TenantContext, get_membership_ctx
from app.core.db import get_db
from app.data import industries
from app.services import industry_trend_service

# Tenant-scoped: the business's own trend brief.
router = APIRouter(prefix="/businesses/{business_id}", tags=["trends"])
# Public: the industry list for the signup/onboarding combobox.
public = APIRouter(tags=["trends"])


@public.get("/industries")
def list_industries() -> dict:
    """Curated industries for the combobox (owners can still type their own)."""
    return {"industries": industries.INDUSTRIES}


@router.get("/trends")
def business_trends(
    ctx: TenantContext = Depends(get_membership_ctx),
    router_ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> dict:
    """The cached trend brief for this business's industry (generated on first
    request, refreshed monthly). 400 if the business has no industry set yet."""
    if not (ctx.business.industry and ctx.business.industry.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set your business industry to see trend suggestions.",
        )
    trend = industry_trend_service.get_or_generate(
        db, router=router_ai, industry=ctx.business.industry
    )
    db.commit()
    return industry_trend_service.as_dict(trend)
