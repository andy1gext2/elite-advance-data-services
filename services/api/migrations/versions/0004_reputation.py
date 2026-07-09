"""reputation: reviews

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-08
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
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
        "reviews",
        *_base_cols(),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("author_name", sa.String(200), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.String(16), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("needs_attention", sa.Boolean(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("business_id", "platform", "external_id", name="uq_review_business_platform_ext"),
    )
    op.create_index("ix_reviews_business_id", "reviews", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_business_id", table_name="reviews")
    op.drop_table("reviews")
