"""Password hashing (bcrypt) and JWT access/refresh tokens (PyJWT).

Passwords are pre-hashed with SHA-256 before bcrypt so inputs longer than bcrypt's
72-byte limit are handled safely.
"""
from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

ACCESS = "access"
REFRESH = "refresh"


# ── Passwords ───────────────────────────────────────
def _prehash(password: str) -> bytes:
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


# ── JWT ─────────────────────────────────────────────
def _encode(sub: str, token_type: str, ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(sub: str) -> str:
    return _encode(sub, ACCESS, timedelta(minutes=settings.jwt_access_ttl_minutes))


def create_refresh_token(sub: str) -> str:
    return _encode(sub, REFRESH, timedelta(days=settings.jwt_refresh_ttl_days))


def decode_token(token: str, expected_type: str | None = None) -> dict:
    """Decode + validate a JWT. Raises jwt.InvalidTokenError on any problem."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("unexpected token type")
    return payload
