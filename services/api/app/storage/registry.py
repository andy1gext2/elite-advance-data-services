"""Storage selection + FastAPI dependency."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import Storage
from app.storage.local import LocalStorage


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    backend = settings.storage_backend.lower()
    if backend == "s3":
        from app.storage.s3 import S3Storage

        return S3Storage(settings)
    return LocalStorage(settings.media_root)


def get_storage_dep() -> Storage:
    return get_storage()
