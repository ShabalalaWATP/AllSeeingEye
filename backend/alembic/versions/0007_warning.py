"""Indicators and alerts (warning).

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "indicators",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False, server_default=""),
        sa.Column("plan_id", sa.Uuid(), nullable=True),
        sa.Column("countries", sa.JSON(), nullable=False),
        sa.Column("west", sa.Float(), nullable=True),
        sa.Column("south", sa.Float(), nullable=True),
        sa.Column("east", sa.Float(), nullable=True),
        sa.Column("north", sa.Float(), nullable=True),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False),
        sa.Column("severity_floor", sa.Float(), nullable=False, server_default="0"),
        sa.Column("report_template", sa.String(40), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_indicators_created_by", "indicators", ["created_by"])
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("indicator_id", sa.Uuid(), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.String(1000), nullable=False, server_default=""),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("event_ids", sa.JSON(), nullable=False),
        sa.Column("countries", sa.JSON(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.Uuid(), nullable=True),
        sa.Column("report_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_alerts_indicator_id", "alerts", ["indicator_id"])
    op.create_index("ix_alerts_fired_at", "alerts", ["fired_at"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("indicators")
