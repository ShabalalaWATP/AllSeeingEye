"""Durable bounded report jobs with owner idempotency and fenced worker leases."""

import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("request_key", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("stage", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("payload_bytes", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("error", sa.String(120), nullable=True),
        sa.UniqueConstraint("owner_id", "request_key", name="uq_report_jobs_owner_request"),
        sa.UniqueConstraint("version_id", name="uq_report_jobs_final_version"),
        sa.CheckConstraint(
            "status IN ('queued','running','paused','completed','needs_review','failed')",
            name="ck_report_jobs_status",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_report_jobs_revision"),
        sa.CheckConstraint(
            "payload_bytes BETWEEN 2 AND 2097152", name="ck_report_jobs_payload_size"
        ),
        sa.CheckConstraint(
            "(status = 'running' AND lease_token IS NOT NULL AND lease_until IS NOT NULL) OR "
            "(status <> 'running' AND lease_token IS NULL AND lease_until IS NULL)",
            name="ck_report_jobs_lease",
        ),
    )
    op.create_index("ix_report_jobs_status_created", "report_jobs", ["status", "created_at", "id"])
    op.create_index("ix_report_jobs_owner_created", "report_jobs", ["owner_id", "created_at"])


def downgrade() -> None:
    table = sa.table("report_jobs", sa.column("id"))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table)):
        raise RuntimeError("Refusing downgrade: retained report jobs remain.")
    op.drop_index("ix_report_jobs_owner_created", table_name="report_jobs")
    op.drop_index("ix_report_jobs_status_created", table_name="report_jobs")
    op.drop_table("report_jobs")
