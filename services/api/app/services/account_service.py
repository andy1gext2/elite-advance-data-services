"""Account-level use-cases for the signed-in user: profile edit, password change,
GDPR-style data export, and self-serve account deletion.

Kept separate from auth_service (signup/login) since these operate on an already
authenticated user and cut across every tenant the user belongs to."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.asset import Asset
from app.models.business import Business
from app.models.campaign import Campaign
from app.models.content import ContentItem
from app.models.enums import Role
from app.models.membership import Membership
from app.models.review import Review
from app.models.schedule import Schedule
from app.models.social_account import SocialAccount
from app.models.user import User


class InvalidPassword(Exception):
    """The supplied current/confirmation password didn't match."""


# Never export secrets: password hashes, encrypted OAuth tokens, storage keys.
_SENSITIVE_COLUMNS = {
    "password_hash",
    "access_token_enc",
    "refresh_token_enc",
    "logo_storage_key",
    "storage_key",
}

# Per business, the child tables we include in an export (all business_id-scoped).
_EXPORT_TABLES: list[tuple[str, type]] = [
    ("content", ContentItem),
    ("campaigns", Campaign),
    ("schedules", Schedule),
    ("reviews", Review),
    ("products", Asset),
    ("connected_accounts", SocialAccount),
]


def update_profile(db: Session, *, user: User, full_name: str | None) -> User:
    user.full_name = full_name
    db.flush()
    return user


def change_password(
    db: Session, *, user: User, current_password: str, new_password: str
) -> None:
    """Change the password after verifying the current one."""
    if not verify_password(current_password, user.password_hash):
        raise InvalidPassword()
    user.password_hash = hash_password(new_password)
    db.flush()


def _json_safe(value):
    if isinstance(value, (uuid.UUID,)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _row(obj) -> dict:
    """Serialize a model row to a dict, dropping sensitive columns."""
    return {
        col.key: _json_safe(getattr(obj, col.key))
        for col in sa_inspect(obj).mapper.column_attrs
        if col.key not in _SENSITIVE_COLUMNS
    }


def export_data(db: Session, *, user: User) -> dict:
    """A portable JSON snapshot of everything the user's account holds — their
    profile plus every business they belong to and its content, campaigns,
    schedules, reviews, products, and connected accounts (tokens excluded)."""
    businesses = list(db.scalars(
        select(Business)
        .join(Membership, Membership.business_id == Business.id)
        .where(Membership.user_id == user.id)
        .order_by(Business.created_at)
    ).all())

    out_businesses = []
    for biz in businesses:
        entry = {"profile": _row(biz)}
        for label, model in _EXPORT_TABLES:
            rows = db.scalars(
                select(model).where(model.business_id == biz.id)
            ).all()
            entry[label] = [_row(r) for r in rows]
        out_businesses.append(entry)

    return {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "account": _row(user),
        "businesses": out_businesses,
    }


def delete_account(db: Session, *, user: User) -> None:
    """Permanently delete the user and every business they OWN (cascading all
    content/schedules/reviews/tokens). Memberships in businesses owned by someone
    else are simply removed, leaving those businesses intact for their owners."""
    owned = db.scalars(
        select(Business)
        .join(Membership, Membership.business_id == Business.id)
        .where(Membership.user_id == user.id, Membership.role == Role.OWNER.value)
    ).all()
    for biz in owned:
        db.delete(biz)  # ON DELETE CASCADE clears its child rows + all memberships
    db.flush()
    db.delete(user)  # cascade removes any remaining (non-owner) memberships
    db.flush()
