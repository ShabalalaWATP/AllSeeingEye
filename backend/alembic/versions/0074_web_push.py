"""Explicit per-device Web Push opt-in. Existing accounts remain unsubscribed."""

import sqlalchemy as sa
from alembic import op

revision = "0074"
down_revision = "0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_push_devices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("security_version", sa.Integer(), nullable=False),
        sa.Column("endpoint_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("encrypted_subscription", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_push_user", "web_push_devices", ["user_id"])
    op.create_index("ix_push_family", "web_push_devices", ["family_id"])
    op.create_index("ix_push_next_check", "web_push_devices", ["next_check_at", "id"])
    op.create_table(
        "web_push_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "device_id",
            sa.Uuid(),
            sa.ForeignKey("web_push_devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_id", "alert_id", name="uq_push_device_alert"),
    )
    op.create_index("ix_push_delivery_state", "web_push_outbox", ["state", "created_at", "id"])


def downgrade() -> None:
    op.drop_table("web_push_outbox")
    op.drop_table("web_push_devices")
