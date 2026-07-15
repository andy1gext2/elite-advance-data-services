"""AI content-calendar schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import Channel, ContentType
from app.schemas.content import ContentItemOut
from app.schemas.scheduling import ScheduleOut

Timeframe = Literal["day", "week", "month", "quarter", "year"]


class PlanIn(BaseModel):
    timeframe: Timeframe = "month"
    theme: str = Field(min_length=1, max_length=2000)


class PlanSlotOut(BaseModel):
    date: str
    channel: str
    recommended_time: str
    topic: str


class PlanOut(BaseModel):
    timeframe: str
    slots: list[PlanSlotOut]


class ScheduleSlotIn(BaseModel):
    """Turn a calendar slot into a scheduled post: generate content from the
    topic, then schedule it. Account is auto-resolved by channel unless given."""
    channel: Channel
    content_type: ContentType = ContentType.SOCIAL_POST
    topic: str = Field(min_length=1, max_length=4000)
    scheduled_at: datetime
    social_account_id: uuid.UUID | None = None


class ScheduleSlotOut(BaseModel):
    content_item: ContentItemOut
    schedule: ScheduleOut
