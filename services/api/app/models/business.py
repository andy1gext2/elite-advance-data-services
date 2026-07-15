"""Business = the tenant. Every domain row elsewhere is scoped by business_id."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.plan import Plan


class Business(BaseModel):
    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120))
    website: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    target_audience: Mapped[str | None] = mapped_column(Text)
    brand_voice: Mapped[str | None] = mapped_column(Text)
    tone: Mapped[str | None] = mapped_column(String(120))
    goals: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)

    # Autopilot: periodically draft a campaign for approval (approve-first).
    autopilot_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    autopilot_theme: Mapped[str | None] = mapped_column(Text)
    autopilot_frequency_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    autopilot_timeframe: Mapped[str] = mapped_column(String(16), default="week", nullable=False)
    autopilot_last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("plans.id"), nullable=True
    )
    plan: Mapped["Plan | None"] = relationship()

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
