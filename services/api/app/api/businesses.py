"""Business (tenant) routes + member management. All tenant-scoped via deps."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_user, get_membership_ctx, require_role
from app.core.db import get_db
from app.models.enums import Role
from app.models.user import User
from app.schemas.business import (
    BusinessCreate,
    BusinessOut,
    MemberInvite,
    MemberOut,
)
from app.services import business_service

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
def create_business(
    body: BusinessCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BusinessOut:
    business = business_service.create_business(
        db, owner=user, data=body.model_dump()
    )
    db.commit()
    db.refresh(business)
    return business


@router.get("", response_model=list[BusinessOut])
def list_my_businesses(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BusinessOut]:
    return business_service.list_businesses_for_user(db, user_id=user.id)


@router.get("/{business_id}", response_model=BusinessOut)
def get_business(ctx: TenantContext = Depends(get_membership_ctx)) -> BusinessOut:
    return ctx.business


@router.get("/{business_id}/members", response_model=list[MemberOut])
def list_members(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> list[MemberOut]:
    return business_service.list_members(db, business_id=ctx.business.id)


@router.post(
    "/{business_id}/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    body: MemberInvite,
    ctx: TenantContext = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> MemberOut:
    try:
        membership = business_service.add_member(
            db, business=ctx.business, email=body.email, role=body.role
        )
    except business_service.PlanLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Plan limit reached: {exc.limit_name} = {exc.limit}. Upgrade to add more.",
        )
    except business_service.UserNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No user with that email")
    except business_service.AlreadyMember:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member")
    db.commit()
    db.refresh(membership)
    return membership
