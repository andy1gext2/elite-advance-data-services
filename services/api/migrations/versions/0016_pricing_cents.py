"""pricing: store advertised price in cents; new $59.99/$149.99/$399.99 ladder

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-18

price_monthly changes unit from whole USD dollars to USD cents so ".99"
prices are exact. Also renames the growth tier's display name Agency -> Growth.
"""
from __future__ import annotations

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE plans SET price_monthly=5999 WHERE tier='starter'")
    op.execute("UPDATE plans SET price_monthly=14999 WHERE tier='professional'")
    op.execute("UPDATE plans SET price_monthly=39999, name='Growth' WHERE tier='growth'")
    op.execute("UPDATE plans SET price_monthly=0 WHERE tier='enterprise'")


def downgrade() -> None:
    # Restore prior whole-dollar values + name.
    op.execute("UPDATE plans SET price_monthly=39 WHERE tier='starter'")
    op.execute("UPDATE plans SET price_monthly=119 WHERE tier='professional'")
    op.execute("UPDATE plans SET price_monthly=349, name='Agency' WHERE tier='growth'")
    op.execute("UPDATE plans SET price_monthly=0 WHERE tier='enterprise'")
