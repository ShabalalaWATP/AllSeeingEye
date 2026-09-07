"""Durable selected-root monitoring and a distinct immutable-transition alert origin."""

import sqlalchemy as sa
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "annotation_monitors",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("notify_on_change", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("unavailable_reason", sa.String(200), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("checkpoint_id", sa.Uuid(), nullable=False),
        sa.Column("checkpoint_number", sa.Integer(), nullable=False),
        sa.Column("checkpoint_payload", sa.Text(), nullable=False),
        sa.Column("checkpoint_sha256", sa.String(64), nullable=False),
        sa.Column("checkpoint_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_annotation_monitors_report_id", "annotation_monitors", ["report_id"])
    op.create_index("ix_annotation_monitors_status", "annotation_monitors", ["status"])
    op.create_index("ix_annotation_monitors_team_id", "annotation_monitors", ["team_id"])
    op.create_index("ix_annotation_monitors_created_by", "annotation_monitors", ["created_by"])
    op.create_table(
        "annotation_monitor_watches",
        sa.Column(
            "monitor_id",
            sa.Uuid(),
            sa.ForeignKey("annotation_monitors.id"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("kind", sa.String(16), nullable=False, primary_key=True),
        sa.Column("root_id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
    )
    op.create_index(
        "ix_annotation_monitor_watches_root_id", "annotation_monitor_watches", ["root_id"]
    )
    op.create_table(
        "annotation_revision_outbox",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("monitor_id", sa.Uuid(), sa.ForeignKey("annotation_monitors.id"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("root_id", sa.Uuid(), nullable=False),
        sa.Column("previous_revision_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("monitor_id", "revision_id", name="uq_annotation_outbox_delivery"),
    )
    op.create_index(
        "ix_annotation_revision_outbox_monitor_id", "annotation_revision_outbox", ["monitor_id"]
    )
    op.create_table(
        "annotation_monitor_transitions",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("monitor_id", sa.Uuid(), sa.ForeignKey("annotation_monitors.id"), nullable=False),
        sa.Column("checkpoint_before", sa.Uuid(), nullable=False),
        sa.Column("checkpoint_after", sa.Uuid(), nullable=False, unique=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_categories", sa.JSON(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=True),
        sa.Column("configuration_revision", sa.Integer(), nullable=False),
        sa.Column("notification_categories", sa.JSON(), nullable=False),
        sa.Column("notify_on_change", sa.Boolean(), nullable=False),
        sa.Column("comparison_sha256", sa.String(64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.UniqueConstraint("monitor_id", "sequence", name="uq_annotation_transition_sequence"),
    )
    op.create_index(
        "ix_annotation_monitor_transitions_monitor_id",
        "annotation_monitor_transitions",
        ["monitor_id"],
    )
    with op.batch_alter_table("alerts") as batch:
        batch.add_column(sa.Column("annotation_monitor_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("annotation_transition_id", sa.Uuid(), nullable=True))
        batch.drop_constraint("ck_alerts_one_origin", type_="check")
        batch.create_check_constraint(
            "ck_alerts_one_origin",
            "(indicator_id IS NOT NULL AND schedule_id IS NULL "
            "AND annotation_monitor_id IS NULL AND annotation_transition_id IS NULL) OR "
            "(indicator_id IS NULL AND schedule_id IS NOT NULL "
            "AND annotation_monitor_id IS NULL AND annotation_transition_id IS NULL) OR "
            "(indicator_id IS NULL AND schedule_id IS NULL "
            "AND annotation_monitor_id IS NOT NULL AND annotation_transition_id IS NOT NULL)",
        )
        batch.create_index("ix_alerts_annotation_monitor_id", ["annotation_monitor_id"])
        batch.create_unique_constraint(
            "uq_alerts_annotation_transition_id", ["annotation_transition_id"]
        )


def downgrade() -> None:
    connection = op.get_bind()
    for table in (
        "annotation_monitors",
        "annotation_monitor_watches",
        "annotation_revision_outbox",
        "annotation_monitor_transitions",
    ):
        if (
            connection.execute(
                sa.select(sa.literal(1)).select_from(sa.table(table)).limit(1)
            ).first()
            is not None
        ):
            raise RuntimeError(
                "Refusing downgrade while retained annotation monitoring history exists"
            )
    if connection.execute(
        sa.text(
            "SELECT 1 FROM alerts WHERE annotation_monitor_id IS NOT NULL OR annotation_transition_id IS NOT NULL LIMIT 1"
        )
    ).first():
        raise RuntimeError("Refusing downgrade while annotation monitor alerts exist")
    with op.batch_alter_table("alerts") as batch:
        batch.drop_constraint("ck_alerts_one_origin", type_="check")
        batch.drop_constraint("uq_alerts_annotation_transition_id", type_="unique")
        batch.drop_index("ix_alerts_annotation_monitor_id")
        batch.drop_column("annotation_transition_id")
        batch.drop_column("annotation_monitor_id")
        batch.create_check_constraint(
            "ck_alerts_one_origin",
            "(indicator_id IS NOT NULL AND schedule_id IS NULL) OR "
            "(indicator_id IS NULL AND schedule_id IS NOT NULL)",
        )
    op.drop_table("annotation_monitor_transitions")
    op.drop_table("annotation_revision_outbox")
    op.drop_table("annotation_monitor_watches")
    op.drop_table("annotation_monitors")
