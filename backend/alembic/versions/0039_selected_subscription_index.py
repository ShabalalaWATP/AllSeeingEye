"""Add a bounded metadata index for explicitly selected subscriptions."""

import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "selected_index_gate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
    )
    op.execute(sa.text("INSERT INTO selected_index_gate (id, revision) VALUES (1, 0)"))
    op.create_table(
        "selected_index_cursors",
        sa.Column("subscription_id", sa.Uuid(), sa.ForeignKey("schedules.id"), primary_key=True),
        sa.Column("source_id", sa.String(100), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("cursor_value", sa.String(512), nullable=True),
        sa.Column("watermark_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_page_key", sa.String(128), nullable=False),
        sa.Column("last_page_sha256", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_selected_cursor_revision"),
    )
    op.create_index("ix_selected_index_cursors_owner_id", "selected_index_cursors", ["owner_id"])
    op.create_table(
        "selected_index_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscription_id", sa.Uuid(), sa.ForeignKey("schedules.id"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("item_key", sa.String(200), nullable=False),
        sa.Column("origin_key", sa.String(300), nullable=False),
        sa.Column("source_version", sa.String(128), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("policy_id", sa.String(100), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("stored_bytes", sa.Integer(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "corrects_id",
            sa.Integer(),
            sa.ForeignKey("selected_index_records.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("corrects_fingerprint", sa.String(64), nullable=True),
        sa.UniqueConstraint(
            "subscription_id", "fingerprint", name="uq_selected_record_fingerprint"
        ),
        sa.CheckConstraint("stored_bytes > 0", name="ck_selected_record_bytes"),
    )
    op.create_index(
        "ix_selected_record_owner_age",
        "selected_index_records",
        ["owner_id", "first_seen_at", "id"],
    )
    op.create_index(
        "ix_selected_record_subscription_source",
        "selected_index_records",
        ["subscription_id", "source_id", "id"],
    )
    op.create_index(
        "ix_selected_record_origin",
        "selected_index_records",
        ["subscription_id", "source_id", "origin_key", "id"],
    )
    op.create_table(
        "selected_index_losses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscription_id", sa.Uuid(), sa.ForeignKey("schedules.id"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("reason", sa.String(24), nullable=False),
        sa.Column("lost_items", sa.Integer(), nullable=False),
        sa.Column("earliest_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "subscription_id", "source_id", "reason", name="uq_selected_loss_scope"
        ),
    )
    op.create_index(
        "ix_selected_loss_subscription",
        "selected_index_losses",
        ["subscription_id", "source_id", "occurred_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("selected_index_records", "selected_index_cursors", "selected_index_losses"):
        query = sa.select(sa.literal(1)).select_from(sa.table(table)).limit(1)
        if bind.execute(query).first() is not None:
            raise RuntimeError("Downgrade would remove selected subscription research history.")
    op.drop_table("selected_index_losses")
    op.drop_table("selected_index_records")
    op.drop_table("selected_index_cursors")
    op.drop_table("selected_index_gate")
