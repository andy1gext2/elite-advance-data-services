"""industry_trends (cached per-industry trend briefs)

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "industry_trends",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("industry", sa.String(length=80), nullable=False),
        sa.Column("display_industry", sa.String(length=120), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_industry_trends_industry"), "industry_trends", ["industry"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_industry_trends_industry"), table_name="industry_trends")
    op.drop_table("industry_trends")
