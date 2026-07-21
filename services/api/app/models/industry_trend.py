"""Cached industry trend brief — shared across all tenants in the same industry.

NOT business-scoped: one row per normalized industry slug, regenerated when the
calendar month rolls over (so seasonal guidance stays current) or the row goes
stale. Businesses read the row matching their industry to power the dashboard's
"Trending in {industry}" suggestions."""
from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class IndustryTrend(BaseModel):
    __tablename__ = "industry_trends"

    # Canonical industry slug (from app.data.industries.normalize) — the cache key.
    industry: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    display_industry: Mapped[str] = mapped_column(String(120), nullable=False)
    # Period tag "YYYY-MM" the brief was generated for (drives monthly refresh).
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    # {keywords[], products[], services[], seasonal[], post_ideas[{title,why,channel}]}
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
