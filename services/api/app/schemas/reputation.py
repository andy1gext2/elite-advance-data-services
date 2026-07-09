"""Reputation (reviews) schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Platform


class ReviewSyncIn(BaseModel):
    # Omit to sync every connected account (falls back to Google Business).
    platform: Platform | None = None


class ReviewSyncOut(BaseModel):
    fetched: int
    new: int


class ReviewResponseIn(BaseModel):
    response_text: str = Field(min_length=1, max_length=8000)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: str
    external_id: str
    author_name: str | None
    rating: int
    body: str
    sentiment: str
    keywords: list[str]
    status: str
    needs_attention: bool
    response_text: str | None
    reviewed_at: datetime | None


class KeywordCount(BaseModel):
    keyword: str
    count: int


class ReputationReportOut(BaseModel):
    total_reviews: int
    average_rating: float
    response_rate: float
    needs_attention: int
    rating_distribution: dict[str, int]
    sentiment: dict[str, int]
    top_compliments: list[KeywordCount]
    top_complaints: list[KeywordCount]
    reviews_this_month: int
    reviews_last_month: int
