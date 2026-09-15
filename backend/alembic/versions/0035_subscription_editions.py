"""Add immutable subscription revisions and a fenced edition ledger."""

import sqlalchemy as sa
from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None

_ACTIVE = "workflow IN ('pending','queued','running','retry_wait','paused','blocked')"


def upgrade() -> None:
    op.create_table(
        "subscription_revisions",
        sa.Column("subscription_id", sa.Uuid(), sa.ForeignKey("schedules.id"), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("request_snapshot", sa.Text(), nullable=False),
        sa.Column("compatibility_fingerprint", sa.String(64), nullable=False),
        sa.Column("recurrence_policy", sa.String(32), nullable=False),
        sa.Column("collection_policy", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("brief_revision_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("revision >= 1", name="ck_subscription_revisions_revision"),
        sa.CheckConstraint(
            "length(request_snapshot) <= 65536", name="ck_subscription_revision_size"
        ),
    )
    op.create_table(
        "subscription_lineages",
        sa.Column("subscription_id", sa.Uuid(), sa.ForeignKey("schedules.id"), primary_key=True),
        sa.Column("compatibility_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "analytical_baseline_version_id",
            sa.Uuid(),
            sa.ForeignKey("report_versions.id"),
            nullable=True,
        ),
        sa.Column("covered_intervals", sa.JSON(), nullable=False),
        sa.Column("complete_cutoff", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_subscription_lineage_revision"),
    )
    op.create_table(
        "subscription_editions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subscription_id", sa.Uuid(), sa.ForeignKey("schedules.id"), nullable=False),
        sa.Column("trigger", sa.String(16), nullable=False),
        sa.Column("due_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_uuid", sa.Uuid(), nullable=True),
        sa.Column("frozen_revision", sa.Integer(), nullable=False),
        sa.Column("requested_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_intervals", sa.JSON(), nullable=False),
        sa.Column("gaps", sa.JSON(), nullable=False),
        sa.Column("compatibility_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "baseline_version_id", sa.Uuid(), sa.ForeignKey("report_versions.id"), nullable=True
        ),
        sa.Column("workflow", sa.String(20), nullable=False),
        sa.Column("report_quality", sa.String(20), nullable=False),
        sa.Column("coverage", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("report_jobs.id"), nullable=True),
        sa.Column("report_id", sa.Uuid(), sa.ForeignKey("reports.id"), nullable=True),
        sa.Column("version_id", sa.Uuid(), sa.ForeignKey("report_versions.id"), nullable=True),
        sa.Column("safe_reason", sa.String(120), nullable=True),
        sa.ForeignKeyConstraint(
            ["subscription_id", "frozen_revision"],
            ["subscription_revisions.subscription_id", "subscription_revisions.revision"],
            name="fk_subscription_edition_revision",
        ),
        sa.UniqueConstraint("subscription_id", "due_at_utc", name="uq_subscription_edition_due"),
        sa.UniqueConstraint(
            "subscription_id", "trigger", "request_uuid", name="uq_subscription_edition_manual"
        ),
        sa.UniqueConstraint("job_id", name="uq_subscription_edition_job"),
        sa.UniqueConstraint("version_id", name="uq_subscription_edition_version"),
        sa.CheckConstraint(
            "(trigger IN ('scheduled','catch_up') AND due_at_utc IS NOT NULL AND "
            "request_uuid IS NULL) OR (trigger IN ('run_now','baseline') AND "
            "due_at_utc IS NULL AND request_uuid IS NOT NULL)",
            name="ck_subscription_edition_trigger",
        ),
        sa.CheckConstraint(
            "workflow IN ('pending','queued','running','retry_wait','paused','blocked',"
            "'completed','failed','cancelled','skipped')",
            name="ck_subscription_edition_workflow",
        ),
        sa.CheckConstraint(
            "report_quality IN ('absent','ready','needs_review','failed')",
            name="ck_subscription_edition_quality",
        ),
        sa.CheckConstraint(
            "coverage IN ('complete_for_plan','partial','insufficient','unknown')",
            name="ck_subscription_edition_coverage",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_subscription_edition_revision"),
        sa.CheckConstraint(
            "requested_start < requested_end", name="ck_subscription_edition_window"
        ),
    )
    op.create_index(
        "ix_subscription_edition_active",
        "subscription_editions",
        ["subscription_id"],
        unique=True,
        sqlite_where=sa.text(_ACTIVE),
        postgresql_where=sa.text(_ACTIVE),
    )
    op.create_index(
        "ix_subscription_edition_due_status",
        "subscription_editions",
        ["workflow", "due_at_utc", "id"],
    )
    op.create_index(
        "ix_subscription_edition_history",
        "subscription_editions",
        ["subscription_id", "created_at", "id"],
    )
    op.create_table(
        "subscription_edition_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "edition_id", sa.Uuid(), sa.ForeignKey("subscription_editions.id"), nullable=False
        ),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("report_jobs.id"), nullable=True),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(120), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(120), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("job_revision", sa.Integer(), nullable=True),
        sa.Column("reserved_requests", sa.Integer(), nullable=False),
        sa.Column("actual_requests", sa.Integer(), nullable=False),
        sa.Column("reserved_output_tokens", sa.Integer(), nullable=False),
        sa.Column("actual_output_tokens", sa.Integer(), nullable=False),
        sa.UniqueConstraint("edition_id", "number", name="uq_subscription_attempt_number"),
        sa.CheckConstraint("number >= 1", name="ck_subscription_attempt_number"),
        sa.CheckConstraint(
            "reserved_requests >= 0 AND actual_requests >= 0 AND "
            "reserved_output_tokens >= 0 AND actual_output_tokens >= 0",
            name="ck_subscription_attempt_usage",
        ),
    )
    op.create_index(
        "ix_subscription_attempt_history", "subscription_edition_attempts", ["edition_id", "number"]
    )
    op.create_table(
        "subscription_delivery_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "edition_id", sa.Uuid(), sa.ForeignKey("subscription_editions.id"), nullable=False
        ),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("destination_ref", sa.Uuid(), nullable=True),
        sa.Column("event_kind", sa.String(80), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_subscription_delivery_key"),
        sa.CheckConstraint("attempts BETWEEN 0 AND 100", name="ck_subscription_delivery_attempts"),
    )
    op.create_index(
        "ix_subscription_delivery_state",
        "subscription_delivery_outbox",
        ["state", "created_at", "id"],
    )
    # Existing history has no trustworthy source-coverage receipt or successful cutoff.
    schedules = sa.table(
        "schedules",
        sa.column("id", sa.Uuid()),
        sa.column("research_options", sa.JSON()),
        sa.column("last_run_at", sa.DateTime(timezone=True)),
        sa.column("last_report_id", sa.Uuid()),
    )
    connection = op.get_bind()
    for row in connection.execute(
        sa.select(schedules.c.id, schedules.c.research_options).where(
            sa.or_(schedules.c.last_run_at.is_not(None), schedules.c.last_report_id.is_not(None))
        )
    ):
        options = dict(row.research_options or {})
        if "last_coverage" not in options:
            options["last_coverage"] = "unknown"
            connection.execute(
                schedules.update().where(schedules.c.id == row.id).values(research_options=options)
            )


def downgrade() -> None:
    connection = op.get_bind()
    for name in (
        "subscription_delivery_outbox",
        "subscription_edition_attempts",
        "subscription_editions",
        "subscription_lineages",
        "subscription_revisions",
    ):
        table = (
            sa.table(name, sa.column("id"))
            if name != "subscription_revisions"
            else sa.table(name, sa.column("subscription_id"))
        )
        if connection.scalar(sa.select(sa.func.count()).select_from(table)):
            raise RuntimeError("Refusing downgrade: retained subscription edition records remain.")
    op.drop_index("ix_subscription_delivery_state", table_name="subscription_delivery_outbox")
    op.drop_table("subscription_delivery_outbox")
    op.drop_index("ix_subscription_attempt_history", table_name="subscription_edition_attempts")
    op.drop_table("subscription_edition_attempts")
    op.drop_index("ix_subscription_edition_history", table_name="subscription_editions")
    op.drop_index("ix_subscription_edition_due_status", table_name="subscription_editions")
    op.drop_index("ix_subscription_edition_active", table_name="subscription_editions")
    op.drop_table("subscription_editions")
    op.drop_table("subscription_lineages")
    op.drop_table("subscription_revisions")
