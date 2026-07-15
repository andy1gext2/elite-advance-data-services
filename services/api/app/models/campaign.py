"""A Campaign is an AI-drafted batch of posts (plan + generated content) that a
human approves before anything is scheduled. Each CampaignItem is one proposed
post: a generated content item + when/where it should go out."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import CampaignSource, CampaignStatus


class Campaign(BaseModel):
    __tablename__ = "campaigns"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    # The product this campaign promotes (optional); its description steers the AI.
    product_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(16), default=CampaignStatus.PROPOSED.value, nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(16), default=CampaignSource.MANUAL.value, nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    items: Mapped[list["CampaignItem"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan",
        order_by="CampaignItem.scheduled_at",
    )


class CampaignItem(BaseModel):
    __tablename__ = "campaign_items"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_items.id", ondelete="SET NULL")
    )
    # Resolved when a matching account is connected; else the item can't be scheduled.
    social_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("social_accounts.id", ondelete="SET NULL")
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    # proposed -> scheduled (on approval) | skipped (no connected account)
    status: Mapped[str] = mapped_column(String(16), default="proposed", nullable=False)

    campaign: Mapped["Campaign"] = relationship(back_populates="items")
