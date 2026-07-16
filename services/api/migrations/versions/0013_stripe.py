"""businesses: Stripe customer/subscription linkage

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("stripe_customer_id", sa.String(64), nullable=True))
    op.add_column("businesses", sa.Column("stripe_subscription_id", sa.String(64), nullable=True))
    op.add_column("businesses", sa.Column("subscription_status", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("businesses", "subscription_status")
    op.drop_column("businesses", "stripe_subscription_id")
    op.drop_column("businesses", "stripe_customer_id")
