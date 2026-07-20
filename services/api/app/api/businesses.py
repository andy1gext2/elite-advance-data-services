"""Business (tenant) routes + member management. All tenant-scoped via deps."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_user, get_membership_ctx, require_role
from app.core.db import get_db
from app.models.enums import Role
from app.models.user import User
from app.schemas.business import (
    BusinessCreate,
    BusinessOut,
    BusinessUpdate,
    MemberInvite,
    MemberOut,
)
from app.services import business_service
from app.storage.base import Storage
from app.storage.registry import get_storage_dep

_MAX_LOGO_BYTES = 5 * 1024 * 1024

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


@router.patch("/{business_id}", response_model=BusinessOut)
def update_business(
    body: BusinessUpdate,
    ctx: TenantContext = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> BusinessOut:
    business = business_service.update_business(
        db, business=ctx.business, data=body.model_dump(exclude_unset=True)
    )
    db.commit()
    db.refresh(business)
    return business


@router.post("/{business_id}/logo", response_model=BusinessOut)
async def upload_logo(
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_role(Role.ADMIN)),
    storage: Storage = Depends(get_storage_dep),
    db: Session = Depends(get_db),
) -> BusinessOut:
    data = await file.read()
    if len(data) > _MAX_LOGO_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Logo too large (max 5 MB)")
    try:
        business = business_service.set_logo(
            db, storage=storage, business=ctx.business,
            data=data, content_type=file.content_type or "",
        )
    except business_service.UnsupportedLogo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logo must be a PNG, JPG, WEBP, or GIF image")
    db.commit()
    db.refresh(business)
    return business


@router.delete("/{business_id}/logo", response_model=BusinessOut)
def delete_logo(
    ctx: TenantContext = Depends(require_role(Role.ADMIN)),
    storage: Storage = Depends(get_storage_dep),
    db: Session = Depends(get_db),
) -> BusinessOut:
    business = business_service.remove_logo(db, storage=storage, business=ctx.business)
    db.commit()
    db.refresh(business)
    return business


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_business(
    ctx: TenantContext = Depends(require_role(Role.OWNER)),
    db: Session = Depends(get_db),
) -> None:
    business_service.delete_business(db, business=ctx.business)
    db.commit()


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
