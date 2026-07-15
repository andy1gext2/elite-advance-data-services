"""An async video-generation job. Video renders take tens of seconds to minutes,
so we persist the provider's operation ref and poll it until it finishes, then
store the bytes and stamp the content item's video_url."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class VideoJob(BaseModel):
    __tablename__ = "video_jobs"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    # processing -> succeeded | failed
    status: Mapped[str] = mapped_column(String(16), default="processing", nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # The provider's long-running-operation handle we poll.
    operation_ref: Mapped[str] = mapped_column(Text, nullable=False)
    video_url: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
