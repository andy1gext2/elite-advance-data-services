"""Scheduling + integrations schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Platform


class ConnectAccountIn(BaseModel):
    platform: Platform
    display_name: str = Field(min_length=1, max_length=200)
    external_id: str | None = None


class SocialAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: str
    display_name: str
    external_id: str | None
    status: str


class ScheduleIn(BaseModel):
    content_item_id: uuid.UUID
    social_account_id: uuid.UUID
    scheduled_at: datetime
    repost_interval_days: int | None = Field(default=None, gt=0)


class BulkScheduleIn(BaseModel):
    items: list[ScheduleIn] = Field(min_length=1, max_length=200)


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_item_id: uuid.UUID
    social_account_id: uuid.UUID
    scheduled_at: datetime
    status: str
    repost_interval_days: int | None
    attempts: int


class RunDueOut(BaseModel):
    due: int
    published: int
    failed: int


class OAuthStartOut(BaseModel):
    # The provider consent URL the frontend redirects the browser to.
    authorize_url: str
