"""Business (tenant) use-cases + tenant-scoped membership management + feature gating."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import UNLIMITED, PlanTier, Role
from app.models.membership import Membership
from app.models.user import User
from app.services.auth_service import get_user_by_email
from app.services.plan_service import get_plan_by_tier


class PlanLimitExceeded(Exception):
    def __init__(self, limit_name: str, limit: int) -> None:
        self.limit_name = limit_name
        self.limit = limit
        super().__init__(f"plan limit '{limit_name}' ({limit}) reached")


class NotAMember(Exception):
    ...


class UserNotFound(Exception):
    ...


class AlreadyMember(Exception):
    ...


def create_business(
    db: Session, *, owner: User, data: dict, default_tier: str = PlanTier.STARTER.value
) -> Business:
    """Create a tenant and make the creator its owner."""
    plan = get_plan_by_tier(db, default_tier)
    business = Business(**data, plan_id=plan.id if plan else None)
    db.add(business)
    db.flush()
    db.add(Membership(user_id=owner.id, business_id=business.id, role=Role.OWNER.value))
    db.flush()
    return business


def update_business(db: Session, *, business: Business, data: dict) -> Business:
    """Patch a tenant's brand/profile details. Only provided fields are changed."""
    for key, value in data.items():
        setattr(business, key, value)
    db.flush()
    return business


_LOGO_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}


class UnsupportedLogo(Exception):
    ...


def set_logo(db: Session, *, storage, business: Business, data: bytes, content_type: str) -> Business:
    """Store a brand logo and point the business at it (replacing any prior logo)."""
    if content_type not in _LOGO_EXT:
        raise UnsupportedLogo(content_type or "unknown")
    old_key = business.logo_storage_key
    key = f"logos/{business.id}/{uuid.uuid4().hex}.{_LOGO_EXT[content_type]}"
    business.logo_url = storage.save(key=key, data=data, content_type=content_type)
    business.logo_storage_key = key
    db.flush()
    if old_key and old_key != key:
        storage.delete(old_key)
    return business


def remove_logo(db: Session, *, storage, business: Business) -> Business:
    if business.logo_storage_key:
        storage.delete(business.logo_storage_key)
    business.logo_url = None
    business.logo_storage_key = None
    db.flush()
    return business


def delete_business(db: Session, *, business: Business) -> None:
    """Delete a tenant and everything scoped to it.

    Child rows (content, schedules, reviews, campaigns, assets, social accounts,
    memberships, …) are removed by the ON DELETE CASCADE on their business_id FK
    — enforced on Postgres, and on SQLite via PRAGMA foreign_keys=ON (see core.db).
    """
    db.delete(business)
    db.flush()


def list_businesses_for_user(db: Session, *, user_id: uuid.UUID) -> list[Business]:
    stmt = (
        select(Business)
        .join(Membership, Membership.business_id == Business.id)
        .where(Membership.user_id == user_id)
        .order_by(Business.created_at)
    )
    return list(db.scalars(stmt).all())


def get_membership(
    db: Session, *, user_id: uuid.UUID, business_id: uuid.UUID
) -> Membership | None:
    return db.scalar(
        select(Membership).where(
            Membership.user_id == user_id, Membership.business_id == business_id
        )
    )


def list_members(db: Session, *, business_id: uuid.UUID) -> list[Membership]:
    return list(
        db.scalars(
            select(Membership).where(Membership.business_id == business_id)
        ).all()
    )


def _member_count(db: Session, business_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count(Membership.id)).where(Membership.business_id == business_id)
    ) or 0


def add_member(
    db: Session, *, business: Business, email: str, role: Role
) -> Membership:
    """Invite an existing user to the tenant, enforcing the plan's max_users limit."""
    limit = business.plan.max_users if business.plan else UNLIMITED
    if limit != UNLIMITED and _member_count(db, business.id) >= limit:
        raise PlanLimitExceeded("max_users", limit)

    user = get_user_by_email(db, email)
    if not user:
        raise UserNotFound(email)
    if get_membership(db, user_id=user.id, business_id=business.id):
        raise AlreadyMember(email)

    membership = Membership(user_id=user.id, business_id=business.id, role=role.value)
    db.add(membership)
    db.flush()
    return membership
