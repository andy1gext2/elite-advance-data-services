"""Auth request/response schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ForgotPasswordOut(BaseModel):
    # Generic acknowledgement (never reveals whether the email exists).
    message: str = "If that email is registered, a reset code is on its way."
    # Present only in non-production (mock email) so you can test without an inbox.
    dev_code: str | None = None


class ResetPasswordIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=8, max_length=128)


class UpdateProfileIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountIn(BaseModel):
    # Require the password to confirm a destructive, irreversible deletion.
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: uuid.UUID
    role: str


class MeOut(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]
    # True when this user is a platform operator (sees the cross-tenant cost view).
    is_platform_admin: bool = False
