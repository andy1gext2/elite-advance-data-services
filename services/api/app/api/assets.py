"""Business asset (product image) upload/list/delete. Tenant-scoped; uploads
require editor+. Max 10 MB per file, common image types only."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_membership_ctx, require_role
from app.core.db import get_db
from app.images.base import ImageProvider, ReferenceImage
from app.images.registry import get_image_provider_dep
from app.models.enums import Role
from app.schemas.asset import AssetOut
from app.services import asset_service, image_service
from app.storage.base import Storage
from app.storage.registry import get_storage_dep

router = APIRouter(prefix="/businesses/{business_id}/assets", tags=["assets"])

MAX_BYTES = 10 * 1024 * 1024


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    file: UploadFile | None = File(default=None),
    kind: str = Form(default="product"),
    name: str | None = Form(default=None),
    description: str | None = Form(default=None),
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    storage: Storage = Depends(get_storage_dep),
    db: Session = Depends(get_db),
) -> AssetOut:
    kind = "service" if kind == "service" else "product"
    name = (name or "").strip() or None
    description = (description or "").strip() or None

    data = await file.read() if file is not None else None
    if data is not None and len(data) > MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 10 MB)")

    # A product needs a photo (its visual baseline); a service can be copy-only.
    if not data and kind != "service":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a photo for a product.")
    if kind == "service" and not (name or description):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add a name or description for the service.")

    try:
        asset = asset_service.create_asset(
            db, storage=storage, business_id=ctx.business.id,
            data=data,
            content_type=(file.content_type or "application/octet-stream") if file else None,
            filename=(file.filename if file else None) or "upload",
            kind=kind, name=name, description=description,
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


@router.post("/{asset_id}/flyer", response_model=AssetOut)
def generate_flyer(
    asset_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    images: ImageProvider = Depends(get_image_provider_dep),
    storage: Storage = Depends(get_storage_dep),
    db: Session = Depends(get_db),
) -> AssetOut:
    """Generate an AI flyer/poster for a service from its description, stored on the
    asset. That exact image is then reused across every post in a campaign that
    promotes this service. Counts against the monthly image quota."""
    try:
        asset = asset_service.get_asset(db, business_id=ctx.business.id, asset_id=asset_id)
    except asset_service.AssetNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    # If the service already has a photo, use it as the flyer's hero visual.
    reference = None
    if asset.storage_key and asset.content_type:
        data = storage.load(asset.storage_key)
        if data:
            reference = ReferenceImage(data=data, mime=asset.content_type)

    try:
        asset = image_service.generate_asset_flyer(
            db, provider=images, storage=storage, business=ctx.business,
            asset=asset, reference=reference,
        )
    except image_service.ImageQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly image limit ({exc.limit}) reached. Upgrade your plan for more.",
        )
    db.commit()
    db.refresh(asset)
    return asset


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
