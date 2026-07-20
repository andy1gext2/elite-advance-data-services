"""Business asset (product photo) use-cases — upload, list, delete. Tenant-scoped;
bytes live in the storage layer, metadata in the DB."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.storage.base import Storage

_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}
_VIDEO_EXT = {"video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm"}
ALLOWED_TYPES = set(_EXT)  # products/services are image-only (AI grounding)
# "Customized media" (kind="media") is a ready-made post, so it also accepts video.
_MEDIA_EXT = {**_EXT, **_VIDEO_EXT}


def _ext_map(kind: str) -> dict:
    return _MEDIA_EXT if kind == "media" else _EXT


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
        ext_map = _ext_map(kind)
        if content_type not in ext_map:
            raise UnsupportedAsset(content_type or "unknown")
        key = f"assets/{business_id}/{uuid.uuid4().hex}.{ext_map[content_type]}"
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


def update_asset(
    db: Session, *, storage: Storage, business_id: uuid.UUID, asset_id: uuid.UUID,
    name: str | None = None, description: str | None = None,
    data: bytes | None = None, content_type: str | None = None,
) -> Asset:
    """Edit a product/service's name, description, and optionally replace its photo."""
    asset = get_asset(db, business_id=business_id, asset_id=asset_id)  # raises AssetNotFound
    if name is not None and name.strip():
        asset.name = name.strip()[:200]
    if description is not None:
        asset.description = description.strip() or None
    if data:
        ext_map = _ext_map(asset.kind)
        if content_type not in ext_map:
            raise UnsupportedAsset(content_type or "unknown")
        old_key = asset.storage_key
        key = f"assets/{business_id}/{uuid.uuid4().hex}.{ext_map[content_type]}"
        asset.url = storage.save(key=key, data=data, content_type=content_type)
        asset.storage_key = key
        asset.content_type = content_type
        if old_key and old_key != key:
            storage.delete(old_key)
    db.flush()
    return asset


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
