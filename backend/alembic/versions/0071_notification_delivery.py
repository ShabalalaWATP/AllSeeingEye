"""Opt-in private notification feed credentials. No existing account is enrolled."""

import sqlalchemy as sa
from alembic import op

revision = "0071"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "private_feed_tokens",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("security_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("include_titles", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
        sa.Column("include_names", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "subscription_notification_preferences",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("subscription_id", sa.Uuid(), sa.ForeignKey("schedules.id"), primary_key=True),
        sa.Column("email_policy", sa.String(24), nullable=False),
        sa.Column("attention", sa.Boolean(), nullable=False),
    )
    op.add_column(
        "subscription_delivery_outbox", sa.Column("lease_token", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "subscription_delivery_outbox",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "subscription_delivery_outbox", sa.Column("safe_reason", sa.String(80), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("subscription_delivery_outbox", "safe_reason")
    op.drop_column("subscription_delivery_outbox", "next_attempt_at")
    op.drop_column("subscription_delivery_outbox", "lease_token")
    op.drop_table("subscription_notification_preferences")
    op.drop_table("notification_preferences")
    op.drop_table("private_feed_tokens")
