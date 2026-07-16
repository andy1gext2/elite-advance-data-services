"""content_items.product_asset_id (auto-ground images on the promoted product)

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_items",
        sa.Column(
            "product_asset_id", sa.Uuid(),
            sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("content_items", "product_asset_id")
