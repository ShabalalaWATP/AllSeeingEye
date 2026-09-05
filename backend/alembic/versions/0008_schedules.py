"""Scheduled products.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("template_id", sa.String(40), nullable=False),
        sa.Column("country_iso", sa.String(2), nullable=True),
        sa.Column("plan_id", sa.Uuid(), nullable=True),
        sa.Column("hour_utc", sa.Integer(), nullable=False),
        sa.Column("cadence", sa.String(16), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_hours", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_report_id", sa.Uuid(), nullable=True),
        sa.Column("last_error", sa.String(300), nullable=True),
    )
    op.create_index("ix_schedules_created_by", "schedules", ["created_by"])
    op.create_index("ix_schedules_next_run_at", "schedules", ["next_run_at"])


def downgrade() -> None:
    op.drop_table("schedules")
