"""Content generation routes. Tenant-scoped; generation/approval require editor+."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.registry import get_ai_router
from app.ai.router import AIRouter
from app.api.deps import TenantContext, get_membership_ctx, require_role
from app.core.db import get_db
from app.models.enums import ContentStatus, Role
from app.schemas.content import (
    ContentItemOut,
    ContentUpdateIn,
    GenerateIn,
    RepurposeIn,
    RepurposeOut,
)
from app.services import content_service

router = APIRouter(prefix="/businesses/{business_id}/content", tags=["content"])


@router.post("/generate", response_model=ContentItemOut, status_code=status.HTTP_201_CREATED)
def generate(
    body: GenerateIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> ContentItemOut:
    try:
        item = content_service.generate_single(
            db, router=ai, business=ctx.business,
            channel=body.channel, content_type=body.content_type,
            brief=body.brief, created_by=ctx.membership.user_id,
        )
    except content_service.AiQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly AI quota ({exc.limit}) reached. Upgrade to generate more.",
        )
    db.commit()
    db.refresh(item)
    return item


@router.post("/repurpose", response_model=RepurposeOut, status_code=status.HTTP_201_CREATED)
def repurpose(
    body: RepurposeIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> RepurposeOut:
    targets = (
        [(t.channel, t.content_type) for t in body.targets] if body.targets else None
    )
    idea, items = content_service.repurpose(
        db, router=ai, business=ctx.business, idea_text=body.idea,
        created_by=ctx.membership.user_id, targets=targets,
    )
    db.commit()
    db.refresh(idea)
    for item in items:
        db.refresh(item)
    return RepurposeOut(idea=idea, items=items)


@router.get("", response_model=list[ContentItemOut])
def list_content(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    channel: str | None = Query(default=None),
) -> list[ContentItemOut]:
    return content_service.list_items(
        db, business_id=ctx.business.id, status=status_filter, channel=channel
    )


@router.get("/{item_id}", response_model=ContentItemOut)
def get_content(
    item_id: uuid.UUID,
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> ContentItemOut:
    try:
        return content_service.get_item(db, business_id=ctx.business.id, item_id=item_id)
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")


@router.patch("/{item_id}", response_model=ContentItemOut)
def update_content(
    item_id: uuid.UUID,
    body: ContentUpdateIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ContentItemOut:
    try:
        item = content_service.update_item(
            db, business_id=ctx.business.id, item_id=item_id,
            title=body.title, body=body.body,
        )
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    db.commit()
    db.refresh(item)
    return item


def _set_status(db: Session, ctx: TenantContext, item_id: uuid.UUID, new: ContentStatus):
    try:
        item = content_service.set_status(
            db, business_id=ctx.business.id, item_id=item_id, status=new
        )
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/approve", response_model=ContentItemOut)
def approve(
    item_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ContentItemOut:
    return _set_status(db, ctx, item_id, ContentStatus.APPROVED)


@router.post("/{item_id}/reject", response_model=ContentItemOut)
def reject(
    item_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ContentItemOut:
    return _set_status(db, ctx, item_id, ContentStatus.REJECTED)
