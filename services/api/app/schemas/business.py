"""Business + membership schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Role


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    industry: str | None = Field(default=None, max_length=120)
    website: str | None = Field(default=None, max_length=255)
    description: str | None = None
    target_audience: str | None = None
    brand_voice: str | None = None
    tone: str | None = Field(default=None, max_length=120)
    goals: str | None = None
    timezone: str = "UTC"


class BusinessUpdate(BaseModel):
    """Partial edit of a tenant's brand/profile. Every field is optional; only
    those present in the request body are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    industry: str | None = Field(default=None, max_length=120)
    website: str | None = Field(default=None, max_length=255)
    description: str | None = None
    target_audience: str | None = None
    brand_voice: str | None = None
    tone: str | None = Field(default=None, max_length=120)
    goals: str | None = None
    timezone: str | None = None


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    industry: str | None
    website: str | None
    description: str | None
    target_audience: str | None
    brand_voice: str | None
    tone: str | None
    goals: str | None
    timezone: str
    status: str
    plan_id: uuid.UUID | None


class MemberInvite(BaseModel):
    email: EmailStr
    role: Role = Role.VIEWER


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    business_id: uuid.UUID
    role: str
