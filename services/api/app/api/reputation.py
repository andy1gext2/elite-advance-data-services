"""Reputation routes: sync reviews, list/respond, reputation report. Tenant-scoped.
Reads require membership; sync/respond require editor+."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.registry import get_ai_router
from app.ai.router import AIRouter
from app.api.deps import TenantContext, get_membership_ctx, require_role
from app.core.db import get_db
from app.models.enums import Role
from app.schemas.reputation import (
    ReputationReportOut,
    ReviewOut,
    ReviewResponseIn,
    ReviewSyncIn,
    ReviewSyncOut,
)
from app.services import reputation_service
from app.services.content_service import AiQuotaExceeded

router = APIRouter(prefix="/businesses/{business_id}", tags=["reputation"])


@router.post("/reviews/sync", response_model=ReviewSyncOut)
def sync_reviews(
    body: ReviewSyncIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ReviewSyncOut:
    platform = body.platform.value if body.platform else None
    summary = reputation_service.sync_reviews(db, business=ctx.business, platform=platform)
    db.commit()
    return ReviewSyncOut(**summary)


@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    sentiment: str | None = Query(default=None),
    needs_attention: bool = Query(default=False),
) -> list[ReviewOut]:
    return reputation_service.list_reviews(
        db, business_id=ctx.business.id, status=status_filter,
        sentiment=sentiment, needs_attention_only=needs_attention,
    )


@router.get("/reviews/{review_id}", response_model=ReviewOut)
def get_review(
    review_id: uuid.UUID,
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> ReviewOut:
    try:
        return reputation_service.get_review(db, business_id=ctx.business.id, review_id=review_id)
    except reputation_service.ReviewNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")


@router.post("/reviews/{review_id}/respond/generate", response_model=ReviewOut)
def generate_response(
    review_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> ReviewOut:
    try:
        review = reputation_service.get_review(db, business_id=ctx.business.id, review_id=review_id)
    except reputation_service.ReviewNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    try:
        review = reputation_service.generate_response(
            db, router=ai, business=ctx.business, review=review
        )
    except AiQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly AI quota ({exc.limit}) reached. Upgrade to draft more.",
        )
    db.commit()
    db.refresh(review)
    return review


@router.patch("/reviews/{review_id}/response", response_model=ReviewOut)
def edit_response(
    review_id: uuid.UUID,
    body: ReviewResponseIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ReviewOut:
    try:
        review = reputation_service.set_response(
            db, business_id=ctx.business.id, review_id=review_id,
            response_text=body.response_text,
        )
    except reputation_service.ReviewNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    db.commit()
    db.refresh(review)
    return review


@router.post("/reviews/{review_id}/respond", response_model=ReviewOut)
def post_response(
    review_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ReviewOut:
    try:
        review = reputation_service.mark_responded(
            db, business_id=ctx.business.id, review_id=review_id
        )
    except reputation_service.ReviewNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    except reputation_service.NothingToPost as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except reputation_service.ReviewReplyFailed as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    db.commit()
    db.refresh(review)
    return review


@router.get("/reputation/report", response_model=ReputationReportOut)
def reputation_report(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> ReputationReportOut:
    return ReputationReportOut(**reputation_service.report(db, business_id=ctx.business.id))
