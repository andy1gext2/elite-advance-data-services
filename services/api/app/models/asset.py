"""A business-uploaded file (product photos, logos, brand imagery). The AI uses
these as a baseline/reference when generating content visuals."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Asset(BaseModel):
    __tablename__ = "assets"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), default="product_image", nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Human label + short description the AI uses as a navigator when writing campaigns.
    name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Public URL (relative /media/… for local, absolute CDN URL for S3).
    url: Mapped[str] = mapped_column(Text, nullable=False)
    # Storage key for deletion / reading back into generation.
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
