"""Explicit scoped alert routes, encrypted destinations and durable delivery intents."""

import sqlalchemy as sa
from alembic import op

revision = "0072"
down_revision = "0071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_webhook_destinations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("url_encrypted", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "alert_notification_routes",
        sa.Column(
            "indicator_id",
            sa.Uuid(),
            sa.ForeignKey("indicators.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("configured_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "webhook_id", sa.Uuid(), sa.ForeignKey("alert_webhook_destinations.id"), nullable=True
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
    )
    op.create_table(
        "alert_notification_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "alert_id", sa.Uuid(), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("channel", sa.String(24), nullable=False),
        sa.Column("destination_ref", sa.String(64), nullable=False),
        sa.Column("route_revision", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("safe_reason", sa.String(48), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("alert_id", "channel", "destination_ref", name="uq_alert_delivery"),
    )
    op.create_index(
        "ix_alert_delivery_pending", "alert_notification_outbox", ["state", "next_attempt_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_alert_delivery_pending", table_name="alert_notification_outbox")
    op.drop_table("alert_notification_outbox")
    op.drop_table("alert_notification_routes")
    op.drop_table("alert_webhook_destinations")
