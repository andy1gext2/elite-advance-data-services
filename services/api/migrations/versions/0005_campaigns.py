"""campaigns + autopilot

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
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
    # Autopilot config on the tenant.
    op.add_column("businesses", sa.Column("autopilot_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("businesses", sa.Column("autopilot_theme", sa.Text(), nullable=True))
    op.add_column("businesses", sa.Column("autopilot_frequency_days", sa.Integer(), nullable=False, server_default="7"))
    op.add_column("businesses", sa.Column("autopilot_timeframe", sa.String(16), nullable=False, server_default="week"))
    op.add_column("businesses", sa.Column("autopilot_last_run_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "campaigns",
        *_base_cols(),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("timeframe", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_campaigns_business_id", "campaigns", ["business_id"])

    op.create_table(
        "campaign_items",
        *_base_cols(),
        sa.Column("campaign_id", sa.Uuid(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_item_id", sa.Uuid(), sa.ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("social_account_id", sa.Uuid(), sa.ForeignKey("social_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
    )
    op.create_index("ix_campaign_items_campaign_id", "campaign_items", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_campaign_items_campaign_id", table_name="campaign_items")
    op.drop_table("campaign_items")
    op.drop_index("ix_campaigns_business_id", table_name="campaigns")
    op.drop_table("campaigns")
    for col in (
        "autopilot_last_run_at", "autopilot_timeframe", "autopilot_frequency_days",
        "autopilot_theme", "autopilot_enabled",
    ):
        op.drop_column("businesses", col)
