"""Shared FastAPI dependencies: DB session, current user, tenant resolution, RBAC.

Multi-tenancy is enforced here: `get_membership_ctx` resolves the caller's role for a
given business_id and 404s if they aren't a member — so routers never see cross-tenant data.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import ACCESS, decode_token
from app.models.business import Business
from app.models.enums import Role
from app.models.membership import Membership
from app.models.user import User
from app.services import business_service

_bearer = HTTPBearer(auto_error=True)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(creds.credentials, expected_type=ACCESS)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise _CREDENTIALS_EXC
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise _CREDENTIALS_EXC
    return user


@dataclass
class TenantContext:
    business: Business
    membership: Membership

    @property
    def role(self) -> Role:
        return Role(self.membership.role)


def get_membership_ctx(
    business_id: uuid.UUID = Path(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    business = db.get(Business, business_id)
    membership = business_service.get_membership(
        db, user_id=user.id, business_id=business_id
    )
    # Same 404 whether the business doesn't exist or the caller isn't a member —
    # don't leak existence of other tenants' resources.
    if not business or not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return TenantContext(business=business, membership=membership)


def require_role(minimum: Role):
    """Dependency factory: require the caller's role to be >= `minimum` for this tenant."""

    def _dep(ctx: TenantContext = Depends(get_membership_ctx)) -> TenantContext:
        if not ctx.role.at_least(minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{minimum.value}' or higher",
            )
        return ctx

    return _dep
