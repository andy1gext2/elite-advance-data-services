"""A business-uploaded product or service the AI markets. Products carry a photo
used as a visual baseline; services are description-first (photo optional — the AI
designs a poster from the copy). The name + description are the AI's navigator."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel

# kind values. Anything other than SERVICE is treated as a product (incl. the
# legacy "product_image").
KIND_PRODUCT = "product"
KIND_SERVICE = "service"


class Asset(BaseModel):
    __tablename__ = "assets"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), default=KIND_PRODUCT, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Human label + short description the AI uses as a navigator when writing campaigns.
    name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(String(100))
    # Public URL (relative /media/… for local, absolute CDN URL for S3).
    # Null for a service with no uploaded photo.
    url: Mapped[str | None] = mapped_column(Text)
    # Storage key for deletion / reading back into generation. Null when no file.
    storage_key: Mapped[str | None] = mapped_column(Text)

    @property
    def is_service(self) -> bool:
        return self.kind == KIND_SERVICE
