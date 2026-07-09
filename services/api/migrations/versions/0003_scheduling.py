"""scheduling: social accounts, schedules, publish jobs

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-08
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
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
        "social_accounts",
        *_base_cols(),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("access_token_enc", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_social_accounts_business_id", "social_accounts", ["business_id"])

    op.create_table(
        "schedules",
        *_base_cols(),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_item_id", sa.Uuid(), sa.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("social_account_id", sa.Uuid(), sa.ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("repost_interval_days", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
    )
    op.create_index("ix_schedules_business_id", "schedules", ["business_id"])
    op.create_index("ix_schedules_scheduled_at", "schedules", ["scheduled_at"])

    op.create_table(
        "publish_jobs",
        *_base_cols(),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), sa.ForeignKey("schedules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content_item_id", sa.Uuid(), sa.ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("social_account_id", sa.Uuid(), sa.ForeignKey("social_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("external_post_id", sa.String(255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_publish_jobs_business_id", "publish_jobs", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_publish_jobs_business_id", table_name="publish_jobs")
    op.drop_table("publish_jobs")
    op.drop_index("ix_schedules_scheduled_at", table_name="schedules")
    op.drop_index("ix_schedules_business_id", table_name="schedules")
    op.drop_table("schedules")
    op.drop_index("ix_social_accounts_business_id", table_name="social_accounts")
    op.drop_table("social_accounts")
