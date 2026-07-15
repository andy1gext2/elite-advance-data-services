"""assets get name+description; campaigns reference a promoted product

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("name", sa.String(200), nullable=True))
    op.add_column("assets", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "campaigns",
        sa.Column(
            "product_asset_id",
            sa.Uuid(),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "product_asset_id")
    op.drop_column("assets", "description")
    op.drop_column("assets", "name")
