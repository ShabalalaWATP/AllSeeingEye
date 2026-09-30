"""Opt-in private notification feed credentials. No existing account is enrolled."""

import sqlalchemy as sa
from alembic import op

revision = "0071"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_digest_preferences",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("hour", sa.Integer(), nullable=False),
        sa.Column("cursor_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("hour BETWEEN 0 AND 23", name="ck_digest_hour"),
    )
    op.create_index(
        "ix_digest_next_due", "notification_digest_preferences", ["enabled", "next_due_at"]
    )
    op.create_table(
        "notification_digest_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("local_day", sa.String(10), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("safe_reason", sa.String(80), nullable=True),
        sa.UniqueConstraint("user_id", "local_day", name="uq_digest_user_day"),
        sa.CheckConstraint("window_start < window_end", name="ck_digest_window"),
        sa.CheckConstraint("attempts BETWEEN 0 AND 3", name="ck_digest_attempts"),
    )
    op.create_index(
        "ix_digest_delivery_state", "notification_digest_outbox", ["state", "created_at", "id"]
    )
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
    op.drop_table("notification_digest_outbox")
    op.drop_table("notification_digest_preferences")
    op.drop_column("subscription_delivery_outbox", "safe_reason")
    op.drop_column("subscription_delivery_outbox", "next_attempt_at")
    op.drop_column("subscription_delivery_outbox", "lease_token")
    op.drop_table("subscription_notification_preferences")
    op.drop_table("notification_preferences")
    op.drop_table("private_feed_tokens")
