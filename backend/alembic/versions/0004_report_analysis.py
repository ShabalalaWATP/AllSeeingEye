"""Direction and devil's advocacy stored beside each report version.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("report_versions", sa.Column("analysis", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("report_versions") as batch:
        batch.drop_column("analysis")
