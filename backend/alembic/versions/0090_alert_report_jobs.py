"""Durable admission and report-job links for new alert-triggered reports."""

import sqlalchemy as sa
from alembic import op

revision = "0090"
down_revision = "0089"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Historical alerts are deliberately not replayed or charged after migration.
    with op.batch_alter_table("alerts") as batch:
        batch.add_column(sa.Column("report_job_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("report_status", sa.String(16), nullable=True))
        batch.add_column(sa.Column("report_error", sa.String(120), nullable=True))
        batch.add_column(
            sa.Column("report_rule_revision", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("report_next_attempt_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.create_foreign_key(
            "fk_alert_report_job", "report_jobs", ["report_job_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_unique_constraint("uq_alert_report_job", ["report_job_id"])
    op.create_index(
        "ix_alert_report_pending", "alerts", ["report_status", "report_next_attempt_at"]
    )


def downgrade() -> None:
    # Dropping outstanding intents or links would permit invisible lost/duplicate work.
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM alerts WHERE report_status IS NOT NULL")):
        raise RuntimeError("Cannot downgrade while alert report history is retained.")
    op.drop_index("ix_alert_report_pending", table_name="alerts")
    with op.batch_alter_table("alerts") as batch:
        batch.drop_constraint("uq_alert_report_job", type_="unique")
        batch.drop_constraint("fk_alert_report_job", type_="foreignkey")
        for name in (
            "report_next_attempt_at",
            "report_rule_revision",
            "report_error",
            "report_status",
            "report_job_id",
        ):
            batch.drop_column(name)
