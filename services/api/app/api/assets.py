"""Business asset (product image) upload/list/delete. Tenant-scoped; uploads
require editor+. Max 10 MB per file, common image types only."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_membership_ctx, require_role
from app.core.db import get_db
from app.models.enums import Role
from app.schemas.asset import AssetOut
from app.services import asset_service
from app.storage.base import Storage
from app.storage.registry import get_storage_dep

router = APIRouter(prefix="/businesses/{business_id}/assets", tags=["assets"])

MAX_BYTES = 10 * 1024 * 1024


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    description: str | None = Form(default=None),
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    storage: Storage = Depends(get_storage_dep),
    db: Session = Depends(get_db),
) -> AssetOut:
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 10 MB)")
    try:
        asset = asset_service.create_asset(
            db, storage=storage, business_id=ctx.business.id,
            data=data, content_type=file.content_type or "application/octet-stream",
            filename=file.filename or "upload",
            name=(name or "").strip() or None,
            description=(description or "").strip() or None,
        )
    except asset_service.UnsupportedAsset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Upload a PNG, JPEG, WebP, or GIF image.",
        )
    db.commit()
    db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetOut])
def list_assets(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> list[AssetOut]:
    return asset_service.list_assets(db, business_id=ctx.business.id)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    storage: Storage = Depends(get_storage_dep),
    db: Session = Depends(get_db),
) -> None:
    try:
        asset_service.delete_asset(db, storage=storage, business_id=ctx.business.id, asset_id=asset_id)
    except asset_service.AssetNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    db.commit()
