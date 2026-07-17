"""assets: support services (description-first, photo optional)

Makes url/storage_key/content_type nullable so a service can exist without an
uploaded photo — the AI designs a poster from its description.

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("assets") as batch:
        batch.alter_column("url", existing_type=sa.Text(), nullable=True)
        batch.alter_column("storage_key", existing_type=sa.Text(), nullable=True)
        batch.alter_column("content_type", existing_type=sa.String(100), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("assets") as batch:
        batch.alter_column("content_type", existing_type=sa.String(100), nullable=False)
        batch.alter_column("storage_key", existing_type=sa.Text(), nullable=False)
        batch.alter_column("url", existing_type=sa.Text(), nullable=False)
