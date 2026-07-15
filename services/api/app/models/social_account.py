"""A connected platform account. OAuth tokens are stored encrypted at rest."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class SocialAccount(BaseModel):
    __tablename__ = "social_accounts"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128))
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Fernet-encrypted OAuth tokens — never stored or logged in plaintext.
    access_token_enc: Mapped[str | None] = mapped_column(Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="connected", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
