"""initial schema: plans, users, businesses, memberships, audit_logs

Revision ID: 0001
Revises:
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
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
        "plans",
        *_base_cols(),
        sa.Column("tier", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=False),
        sa.Column("max_social_accounts", sa.Integer(), nullable=False),
        sa.Column("max_locations", sa.Integer(), nullable=False),
        sa.Column("ai_monthly_quota", sa.Integer(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
    )

    op.create_table(
        "users",
        *_base_cols(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "businesses",
        *_base_cols(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("industry", sa.String(120), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("brand_voice", sa.Text(), nullable=True),
        sa.Column("tone", sa.String(120), nullable=True),
        sa.Column("goals", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("plan_id", sa.Uuid(), sa.ForeignKey("plans.id"), nullable=True),
    )

    op.create_table(
        "memberships",
        *_base_cols(),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.UniqueConstraint("user_id", "business_id", name="uq_user_business"),
    )
    op.create_index("ix_memberships_business_id", "memberships", ["business_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])

    op.create_table(
        "audit_logs",
        *_base_cols(),
        sa.Column("business_id", sa.Uuid(), sa.ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity", sa.String(80), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("ip", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_index("ix_memberships_business_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_table("businesses")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("plans")
