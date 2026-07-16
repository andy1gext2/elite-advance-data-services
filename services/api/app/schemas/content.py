"""Content generation request/response schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import Channel, ContentType


class GenerateIn(BaseModel):
    channel: Channel
    content_type: ContentType = ContentType.SOCIAL_POST
    brief: str = Field(min_length=1, max_length=4000)


class ContentUpdateIn(BaseModel):
    """Edit a piece's copy. Omit a field to leave it unchanged."""
    title: str | None = Field(default=None, max_length=255)
    body: str | None = Field(default=None, min_length=1, max_length=20000)

    @model_validator(mode="after")
    def _at_least_one(self) -> "ContentUpdateIn":
        if self.title is None and self.body is None:
            raise ValueError("Provide title or body to update")
        return self


class RepurposeTarget(BaseModel):
    channel: Channel
    content_type: ContentType


class RepurposeIn(BaseModel):
    idea: str = Field(min_length=1, max_length=4000)
    # Omit to use the default 12-variant pipeline.
    targets: list[RepurposeTarget] | None = None


class ContentItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    idea_id: uuid.UUID | None
    product_asset_id: uuid.UUID | None = None
    channel: str
    content_type: str
    title: str | None
    body: str
    meta: dict
    status: str
    image_url: str | None = None
    image_prompt: str | None = None
    video_url: str | None = None


class VideoJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_item_id: uuid.UUID
    status: str  # processing | succeeded | failed
    video_url: str | None = None
    error: str | None = None
    prompt: str | None = None  # the 8-second vision Claude wrote for Veo


class VideoCreditsIn(BaseModel):
    quantity: int = Field(ge=1, le=1000)


class VideoStartIn(BaseModel):
    # Optional edited vision/script; omit to have Claude write it.
    prompt: str | None = Field(default=None, max_length=4000)


class VideoScriptOut(BaseModel):
    prompt: str


class ContentIdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brief: str
    goal: str | None


class RepurposeOut(BaseModel):
    idea: ContentIdeaOut
    items: list[ContentItemOut]
