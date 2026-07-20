"""businesses.logo_url + logo_storage_key (brand logo)

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("logo_url", sa.String(length=500), nullable=True))
    op.add_column("businesses", sa.Column("logo_storage_key", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("businesses", "logo_storage_key")
    op.drop_column("businesses", "logo_url")
