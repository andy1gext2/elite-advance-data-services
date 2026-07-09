"""content: ideas, items, ai usage

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_now = sa.text("now()")


def _base_cols() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "content_ideas",
        *_base_cols(),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column("goal", sa.String(255), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_content_ideas_business_id", "content_ideas", ["business_id"])

    op.create_table(
        "content_items",
        *_base_cols(),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idea_id", sa.Uuid(), sa.ForeignKey("content_ideas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_content_items_business_id", "content_items", ["business_id"])

    op.create_table(
        "ai_usage",
        *_base_cols(),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module", sa.String(48), nullable=False),
        sa.Column("provider", sa.String(48), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
    )
    op.create_index("ix_ai_usage_business_id", "ai_usage", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_usage_business_id", table_name="ai_usage")
    op.drop_table("ai_usage")
    op.drop_index("ix_content_items_business_id", table_name="content_items")
    op.drop_table("content_items")
    op.drop_index("ix_content_ideas_business_id", table_name="content_ideas")
    op.drop_table("content_ideas")
