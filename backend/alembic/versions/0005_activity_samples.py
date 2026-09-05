"""Hourly activity samples for baselines (military flights per nation and the like).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activity_samples",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("hour", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.UniqueConstraint("kind", "key", "hour", name="uq_activity_samples_kind_key_hour"),
    )
    op.create_index("ix_activity_samples_kind_hour", "activity_samples", ["kind", "hour"])


def downgrade() -> None:
    op.drop_table("activity_samples")
