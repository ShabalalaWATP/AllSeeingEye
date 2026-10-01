"""Administrator evaluation runs with a single active slot and a bounded artefact.

The integrator re-chains this revision after the open 0067-0074 work.
"""

import sqlalchemy as sa
from alembic import op

revision = "0076"
down_revision = "0066"
branch_labels = None
depends_on = None

# Kept literal so later model edits cannot rewrite this historical migration.
CHECKS = (
    ("status IN ('running', 'completed', 'cancelled', 'stopped')", "ck_evaluation_runs_status"),
    (
        "(status = 'running' AND active_slot = 1) OR (status <> 'running' AND active_slot IS NULL)",
        "ck_evaluation_runs_active_slot",
    ),
    ("max_calls BETWEEN 1 AND 200", "ck_evaluation_runs_max_calls"),
    ("calls_reserved BETWEEN 0 AND max_calls", "ck_evaluation_runs_calls_reserved"),
    ("calls_failed BETWEEN 0 AND calls_reserved", "ck_evaluation_runs_calls_failed"),
)


def upgrade() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "actor_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_evaluation_runs_actor"),
            nullable=True,
        ),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("profile_name", sa.String(80), nullable=False),
        sa.Column("model", sa.String(2048), nullable=False),
        sa.Column("profile_fingerprint", sa.String(64), nullable=False),
        sa.Column("case_ids", sa.JSON(), nullable=False),
        sa.Column("case_fingerprints", sa.JSON(), nullable=False),
        sa.Column("max_calls", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("stop_reason", sa.String(32), nullable=True),
        sa.Column("active_slot", sa.Integer(), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("calls_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calls_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("artefact", sa.LargeBinary(), nullable=True),
        sa.Column("has_artefact", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("active_slot", name="uq_evaluation_runs_active_slot"),
        *(sa.CheckConstraint(sql, name=name) for sql, name in CHECKS),
    )
    op.create_index("ix_evaluation_runs_created_at", "evaluation_runs", ["created_at"])


def downgrade() -> None:
    # Evaluation runs are disposable operational records; nothing else references them.
    op.drop_index("ix_evaluation_runs_created_at", table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
