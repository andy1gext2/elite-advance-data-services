"""Auth routes: signup, login, refresh, me."""
from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import (
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordIn,
    DeleteAccountIn,
    ForgotPasswordIn,
    ForgotPasswordOut,
    LoginIn,
    MeOut,
    RefreshIn,
    ResetPasswordIn,
    SignupIn,
    TokenOut,
    UpdateProfileIn,
)
from app.core.security import verify_password
from app.services import account_service, auth_service, password_reset_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(user: User) -> TokenOut:
    sub = str(user.id)
    return TokenOut(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
    )


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupIn, db: Session = Depends(get_db)) -> TokenOut:
    try:
        user = auth_service.signup(
            db, email=body.email, password=body.password, full_name=body.full_name
        )
    except auth_service.EmailAlreadyRegistered:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    db.commit()
    return _tokens(user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    try:
        user = auth_service.authenticate(db, email=body.email, password=body.password)
    except auth_service.InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return _tokens(user)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    try:
        payload = decode_token(body.refresh_token, expected_type=REFRESH)
        user = db.get(User, uuid.UUID(payload["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError):
        user = None
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return _tokens(user)


@router.post("/forgot-password", response_model=ForgotPasswordOut)
def forgot_password(body: ForgotPasswordIn, db: Session = Depends(get_db)) -> ForgotPasswordOut:
    """Email a single-use reset code. Always returns the same generic message so
    it can't be used to probe which emails are registered."""
    code = password_reset_service.request_reset(db, email=body.email)
    db.commit()
    # Only surface the code outside production (mock email) so you can test
    # without a real inbox; production never returns it.
    dev_code = code if (code and not get_settings().is_production) else None
    return ForgotPasswordOut(dev_code=dev_code)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(body: ResetPasswordIn, db: Session = Depends(get_db)) -> None:
    """Verify the emailed code and set a new password."""
    try:
        password_reset_service.reset_password(
            db, email=body.email, code=body.code, new_password=body.new_password
        )
    except password_reset_service.InvalidResetCode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code.",
        )
    db.commit()


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)) -> MeOut:
    is_admin = user.email.lower() in get_settings().admin_emails
    return MeOut(user=user, memberships=user.memberships, is_platform_admin=is_admin)


@router.patch("/me", response_model=MeOut)
def update_me(
    body: UpdateProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeOut:
    account_service.update_profile(db, user=user, full_name=body.full_name)
    db.commit()
    db.refresh(user)
    is_admin = user.email.lower() in get_settings().admin_emails
    return MeOut(user=user, memberships=user.memberships, is_platform_admin=is_admin)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        account_service.change_password(
            db, user=user,
            current_password=body.current_password, new_password=body.new_password,
        )
    except account_service.InvalidPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect."
        )
    db.commit()


@router.get("/export")
def export_account(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Download a full JSON copy of the account's data (GDPR data portability)."""
    return account_service.export_data(db, user=user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    body: DeleteAccountIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Permanently delete the account and every business the user owns."""
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect."
        )
    account_service.delete_account(db, user=user)
    db.commit()
