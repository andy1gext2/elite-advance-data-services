"""pricing: image quota + price on plans, video credits on businesses; retune tiers

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("image_monthly_quota", sa.Integer(), nullable=False, server_default="40"))
    op.add_column("plans", sa.Column("price_monthly", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("businesses", sa.Column("video_credits", sa.Integer(), nullable=False, server_default="0"))

    # Retune existing plan rows to the recommended tiers (-1 == unlimited).
    op.execute("""
        UPDATE plans SET price_monthly=39, max_social_accounts=5, max_locations=1,
            ai_monthly_quota=150, image_monthly_quota=40, video_monthly_quota=1
        WHERE tier='starter'
    """)
    op.execute("""
        UPDATE plans SET price_monthly=119, max_social_accounts=15, max_locations=3,
            ai_monthly_quota=1000, image_monthly_quota=250, video_monthly_quota=8
        WHERE tier='professional'
    """)
    op.execute("""
        UPDATE plans SET name='Agency', price_monthly=349, max_social_accounts=60, max_locations=20,
            ai_monthly_quota=5000, image_monthly_quota=1000, video_monthly_quota=30
        WHERE tier='growth'
    """)
    op.execute("""
        UPDATE plans SET price_monthly=0, image_monthly_quota=-1, video_monthly_quota=-1
        WHERE tier='enterprise'
    """)


def downgrade() -> None:
    op.drop_column("businesses", "video_credits")
    op.drop_column("plans", "price_monthly")
    op.drop_column("plans", "image_monthly_quota")
