"""social_accounts.refresh_token_enc (keep OAuth sessions alive)

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("social_accounts", sa.Column("refresh_token_enc", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("social_accounts", "refresh_token_enc")
