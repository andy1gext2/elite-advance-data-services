"""plans.video_monthly_quota (cost guard for paid video renders)

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plans",
        sa.Column("video_monthly_quota", sa.Integer(), nullable=False, server_default="5"),
    )
    # Per-tier caps (video renders are paid + expensive). -1 == unlimited.
    op.execute("UPDATE plans SET video_monthly_quota = 30 WHERE tier = 'professional'")
    op.execute("UPDATE plans SET video_monthly_quota = 100 WHERE tier = 'growth'")
    op.execute("UPDATE plans SET video_monthly_quota = -1 WHERE tier = 'enterprise'")


def downgrade() -> None:
    op.drop_column("plans", "video_monthly_quota")
