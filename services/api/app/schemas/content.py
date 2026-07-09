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
    channel: str
    content_type: str
    title: str | None
    body: str
    meta: dict
    status: str


class ContentIdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brief: str
    goal: str | None


class RepurposeOut(BaseModel):
    idea: ContentIdeaOut
    items: list[ContentItemOut]
