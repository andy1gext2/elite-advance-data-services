"""content_items.video_url + video_jobs (async video generation)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_now = sa.text("now()")


def upgrade() -> None:
    op.add_column("content_items", sa.Column("video_url", sa.Text(), nullable=True))
    op.create_table(
        "video_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_item_id", sa.Uuid(), sa.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("operation_ref", sa.Text(), nullable=False),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_video_jobs_business_id", "video_jobs", ["business_id"])
    op.create_index("ix_video_jobs_content_item_id", "video_jobs", ["content_item_id"])


def downgrade() -> None:
    op.drop_index("ix_video_jobs_content_item_id", table_name="video_jobs")
    op.drop_index("ix_video_jobs_business_id", table_name="video_jobs")
    op.drop_table("video_jobs")
    op.drop_column("content_items", "video_url")
