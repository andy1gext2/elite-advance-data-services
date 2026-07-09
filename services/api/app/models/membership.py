"""User <-> Business link carrying the RBAC role. This is the tenancy join."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import Role

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.user import User


class Membership(BaseModel):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "business_id", name="uq_user_business"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), default=Role.OWNER.value, nullable=False)

    user: Mapped["User"] = relationship(back_populates="memberships")
    business: Mapped["Business"] = relationship(back_populates="memberships")
