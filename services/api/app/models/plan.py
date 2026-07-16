"""Subscription plan + limits used for feature gating."""
from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import BaseModel


class Plan(BaseModel):
    __tablename__ = "plans"

    tier: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    # Limits ( -1 == unlimited, see enums.UNLIMITED )
    max_users: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    max_social_accounts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    max_locations: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ai_monthly_quota: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    # Images cost more than text, video far more — each gets its own monthly cap.
    image_monthly_quota: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    video_monthly_quota: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Advertised price, USD/month (0 = custom/contact sales).
    price_monthly: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Boolean feature flags: white_label, advanced_analytics, priority_support, ...
    features: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
