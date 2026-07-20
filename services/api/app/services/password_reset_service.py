"""Forgot-password flow: email a single-use 6-digit code, then verify it to set
a new password. Codes are hashed at rest, expire, are single-use, and are rate-
limited by attempt count."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.email.base import EmailMessage
from app.email.registry import get_email_provider
from app.models.password_reset import PasswordReset
from app.services.auth_service import get_user_by_email

logger = logging.getLogger("app.email")


class InvalidResetCode(Exception):
    ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    """Treat a stored naive datetime (SQLite) as UTC so comparisons don't raise."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def request_reset(db: Session, *, email: str) -> str | None:
    """Create + email a reset code for `email` if a user exists. Returns the
    plaintext code (for dev echo only) or None if no such user. Caller must not
    reveal which case occurred (avoid account enumeration)."""
    user = get_user_by_email(db, email)
    if not user:
        return None

    s = get_settings()
    # Invalidate any outstanding codes for this user — only the newest works.
    db.execute(
        update(PasswordReset)
        .where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None))
        .values(used_at=_now())
    )

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(PasswordReset(
        user_id=user.id,
        code_hash=hash_password(code),
        expires_at=_now() + timedelta(minutes=s.reset_code_ttl_minutes),
    ))
    db.flush()

    # Best-effort send: a mail-provider failure (bad SMTP config, unverified
    # sender) must not 500 the request or reveal that the email exists. Log it so
    # the operator can diagnose from the server logs.
    try:
        get_email_provider().send(EmailMessage(
            to=user.email,
            subject="Your Elite Advance password reset code",
            text=(
                f"Your password reset code is: {code}\n\n"
                f"Enter it on the reset page to choose a new password. "
                f"This code expires in {s.reset_code_ttl_minutes} minutes.\n\n"
                f"If you didn't request this, you can ignore this email."
            ),
            html=(
                f"<p>Your password reset code is:</p>"
                f"<p style='font-size:24px;font-weight:700;letter-spacing:3px'>{code}</p>"
                f"<p>Enter it on the reset page to choose a new password. "
                f"This code expires in {s.reset_code_ttl_minutes} minutes.</p>"
                f"<p style='color:#888'>If you didn't request this, you can ignore this email.</p>"
            ),
        ))
    except Exception:  # noqa: BLE001 — never surface mail errors to the caller
        logger.exception("Failed to send password-reset email to %s", user.email)
    return code


def reset_password(db: Session, *, email: str, code: str, new_password: str) -> None:
    """Verify the code and set a new password. Raises InvalidResetCode on any
    failure (unknown user, no/expired/spent code, too many attempts, wrong code)."""
    s = get_settings()
    user = get_user_by_email(db, email)
    if not user:
        raise InvalidResetCode()

    reset = db.scalar(
        select(PasswordReset)
        .where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None))
        .order_by(PasswordReset.created_at.desc())
    )
    if not reset or _aware(reset.expires_at) < _now():
        raise InvalidResetCode()
    if reset.attempts >= s.reset_max_attempts:
        reset.used_at = _now()  # burn it — force a new request
        db.flush()
        raise InvalidResetCode()

    reset.attempts += 1
    if not verify_password(code, reset.code_hash):
        db.flush()
        raise InvalidResetCode()

    user.password_hash = hash_password(new_password)
    reset.used_at = _now()
    db.flush()
