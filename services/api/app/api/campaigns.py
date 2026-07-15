"""Campaigns + autopilot. Tenant-scoped. Reads require membership; propose/approve/
reject and autopilot config require editor+. Approve-first: nothing schedules until
a human approves."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.registry import get_ai_router
from app.ai.router import AIRouter
from app.api.deps import TenantContext, get_membership_ctx, require_role
from app.core.db import get_db
from app.models.campaign import Campaign
from app.models.content import ContentItem
from app.models.enums import CampaignSource, Role
from app.models.social_account import SocialAccount
from app.schemas.campaign import (
    AutopilotConfigIn,
    AutopilotConfigOut,
    CampaignCalendarItemOut,
    CampaignDetailOut,
    CampaignItemOut,
    CampaignOut,
    ProposeCampaignIn,
)
from app.services import asset_service, campaign_service
from app.services.content_service import AiQuotaExceeded

router = APIRouter(prefix="/businesses/{business_id}", tags=["campaigns"])


def _detail(db: Session, campaign: Campaign) -> CampaignDetailOut:
    items = []
    for it in campaign.items:
        content = db.get(ContentItem, it.content_item_id) if it.content_item_id else None
        account = db.get(SocialAccount, it.social_account_id) if it.social_account_id else None
        items.append(CampaignItemOut(
            id=it.id, channel=it.channel, scheduled_at=it.scheduled_at, status=it.status,
            content_item_id=it.content_item_id, social_account_id=it.social_account_id,
            body=content.body if content else None,
            title=content.title if content else None,
            account_name=account.display_name if account else None,
        ))
    return CampaignDetailOut(
        id=campaign.id, name=campaign.name, timeframe=campaign.timeframe,
        status=campaign.status, source=campaign.source, created_at=campaign.created_at,
        items=items,
    )


@router.post("/campaigns/propose", response_model=CampaignDetailOut, status_code=status.HTTP_201_CREATED)
def propose_campaign(
    body: ProposeCampaignIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> CampaignDetailOut:
    product = None
    if body.product_asset_id is not None:
        try:
            product = asset_service.get_asset(
                db, business_id=ctx.business.id, asset_id=body.product_asset_id
            )
        except asset_service.AssetNotFound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    try:
        campaign = campaign_service.propose(
            db, router=ai, business=ctx.business, theme=body.theme,
            timeframe=body.timeframe, source=CampaignSource.MANUAL,
            created_by=ctx.membership.user_id, product=product,
        )
    except AiQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly AI quota ({exc.limit}) reached. Upgrade to draft campaigns.",
        )
    db.commit()
    db.refresh(campaign)
    return _detail(db, campaign)


@router.get("/campaigns/calendar", response_model=list[CampaignCalendarItemOut])
def campaign_calendar(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> list[CampaignCalendarItemOut]:
    """Bird's-eye schedule: every campaign's posts as dated calendar entries."""
    return campaign_service.calendar_items(db, business_id=ctx.business.id)


@router.get("/campaigns", response_model=list[CampaignOut])
def list_campaigns(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[CampaignOut]:
    return campaign_service.list_campaigns(db, business_id=ctx.business.id, status=status_filter)


@router.get("/campaigns/{campaign_id}", response_model=CampaignDetailOut)
def get_campaign(
    campaign_id: uuid.UUID,
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> CampaignDetailOut:
    try:
        campaign = campaign_service.get(db, business_id=ctx.business.id, campaign_id=campaign_id)
    except campaign_service.CampaignNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return _detail(db, campaign)


def _transition(db, ctx, campaign_id, action):
    try:
        campaign = action(db, business_id=ctx.business.id, campaign_id=campaign_id)
    except campaign_service.CampaignNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    except campaign_service.InvalidCampaignState as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    db.commit()
    db.refresh(campaign)
    return _detail(db, campaign)


@router.post("/campaigns/{campaign_id}/approve", response_model=CampaignDetailOut)
def approve_campaign(
    campaign_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> CampaignDetailOut:
    return _transition(db, ctx, campaign_id, campaign_service.approve)


@router.post("/campaigns/{campaign_id}/reject", response_model=CampaignDetailOut)
def reject_campaign(
    campaign_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> CampaignDetailOut:
    return _transition(db, ctx, campaign_id, campaign_service.reject)


# ── Autopilot config ────────────────────────────────
@router.get("/autopilot", response_model=AutopilotConfigOut)
def get_autopilot(
    ctx: TenantContext = Depends(get_membership_ctx),
) -> AutopilotConfigOut:
    return ctx.business


@router.put("/autopilot", response_model=AutopilotConfigOut)
def set_autopilot(
    body: AutopilotConfigIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> AutopilotConfigOut:
    b = ctx.business
    b.autopilot_enabled = body.autopilot_enabled
    b.autopilot_theme = body.autopilot_theme
    b.autopilot_frequency_days = body.autopilot_frequency_days
    b.autopilot_timeframe = body.autopilot_timeframe
    db.commit()
    db.refresh(b)
    return b
