"""Business asset (product photo) use-cases — upload, list, delete. Tenant-scoped;
bytes live in the storage layer, metadata in the DB."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.storage.base import Storage

_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}
ALLOWED_TYPES = set(_EXT)


class AssetNotFound(Exception):
    ...


class UnsupportedAsset(Exception):
    ...


def create_asset(
    db: Session, *, storage: Storage, business_id: uuid.UUID,
    data: bytes | None = None, content_type: str | None = None,
    filename: str | None = None, kind: str = "product",
    name: str | None = None, description: str | None = None,
) -> Asset:
    """Create a product or service. A photo is optional for services (data=None) —
    they're described in copy and the AI designs a poster from it."""
    url = key = None
    if data:
        if content_type not in ALLOWED_TYPES:
            raise UnsupportedAsset(content_type or "unknown")
        ext = _EXT[content_type]
        key = f"assets/{business_id}/{uuid.uuid4().hex}.{ext}"
        url = storage.save(key=key, data=data, content_type=content_type)
    label = name or filename or "Untitled"
    asset = Asset(
        business_id=business_id, kind=kind, filename=(filename or label)[:255],
        name=label[:200], description=description or None,
        content_type=content_type if data else None, url=url, storage_key=key,
    )
    db.add(asset)
    db.flush()
    return asset


def list_assets(db: Session, *, business_id: uuid.UUID) -> list[Asset]:
    return list(db.scalars(
        select(Asset).where(Asset.business_id == business_id).order_by(Asset.created_at.desc())
    ).all())


def get_asset(db: Session, *, business_id: uuid.UUID, asset_id: uuid.UUID) -> Asset:
    asset = db.scalar(
        select(Asset).where(Asset.id == asset_id, Asset.business_id == business_id)
    )
    if not asset:
        raise AssetNotFound(str(asset_id))
    return asset


def delete_asset(db: Session, *, storage: Storage, business_id: uuid.UUID, asset_id: uuid.UUID) -> None:
    asset = get_asset(db, business_id=business_id, asset_id=asset_id)
    if asset.storage_key:
        storage.delete(asset.storage_key)
    db.delete(asset)
    db.flush()
