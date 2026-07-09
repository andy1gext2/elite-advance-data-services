"""Customer review captured from a platform (Google, Facebook, …).

Ingested via the connector layer, enriched with heuristic sentiment + keywords,
and optionally answered with an AI-drafted response. Deduped per tenant by
(business_id, platform, external_id)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import BaseModel
from app.models.enums import ReviewSentiment, ReviewStatus


class Review(BaseModel):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint(
            "business_id", "platform", "external_id", name="uq_review_business_platform_ext"
        ),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    # The platform's own id for the review — the dedup key on re-sync.
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(200))
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Derived on ingest (heuristic; replaceable by the AI SENTIMENT module).
    sentiment: Mapped[str] = mapped_column(
        String(16), default=ReviewSentiment.NEUTRAL.value, nullable=False
    )
    keywords: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    status: Mapped[str] = mapped_column(
        String(32), default=ReviewStatus.NEW.value, nullable=False
    )
    # Escalation recommendation: low rating / negative sentiment awaiting a reply.
    needs_attention: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    response_text: Mapped[str | None] = mapped_column(Text)

    # When the review was posted on the platform (not when we ingested it).
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
