"""Symmetric encryption for secrets at rest (OAuth tokens, API keys).

Uses Fernet (AES-128-CBC + HMAC). Key comes from FERNET_KEY; in non-production a
deterministic dev key is derived from APP_SECRET_KEY so the app runs without extra
config. Production requires an explicit FERNET_KEY.
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.fernet_key
    if not key:
        if settings.is_production:
            raise RuntimeError("FERNET_KEY is required in production")
        # Deterministic dev-only key derived from the app secret.
        digest = hashlib.sha256(settings.app_secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key if isinstance(key, bytes) else key.encode())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
