"""Campaign + autopilot schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.calendar import Timeframe


class ProposeCampaignIn(BaseModel):
    theme: str = Field(min_length=1, max_length=2000)
    timeframe: Timeframe = "week"
    # Optional product to promote; its description steers the AI.
    product_asset_id: uuid.UUID | None = None
    # Day the campaign starts (defaults to today).
    start_date: date | None = None


class CampaignCalendarItemOut(BaseModel):
    """One dated post for the calendar bird's-eye view."""
    id: uuid.UUID
    campaign_id: uuid.UUID
    campaign_name: str
    channel: str
    scheduled_at: datetime
    status: str
    content_item_id: uuid.UUID | None = None
    title: str | None = None
    body: str | None = None


class CampaignItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel: str
    scheduled_at: datetime
    status: str
    content_item_id: uuid.UUID | None
    social_account_id: uuid.UUID | None
    # Denormalized for display (filled by the route).
    body: str | None = None
    title: str | None = None
    image_url: str | None = None
    account_name: str | None = None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    timeframe: str
    status: str
    source: str
    created_at: datetime


class CampaignDetailOut(CampaignOut):
    items: list[CampaignItemOut]


class AutopilotConfigIn(BaseModel):
    autopilot_enabled: bool
    autopilot_theme: str | None = Field(default=None, max_length=2000)
    autopilot_frequency_days: int = Field(default=7, ge=1, le=90)
    autopilot_timeframe: Timeframe = "week"


class AutopilotConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    autopilot_enabled: bool
    autopilot_theme: str | None
    autopilot_frequency_days: int
    autopilot_timeframe: str
    autopilot_last_run_at: datetime | None
