"""assets: business-uploaded product/brand images

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_now = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
    )
    op.create_index("ix_assets_business_id", "assets", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_assets_business_id", table_name="assets")
    op.drop_table("assets")
