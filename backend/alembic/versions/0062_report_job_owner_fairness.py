"""Limit durable report execution to one running job per owner."""

import sqlalchemy as sa
from alembic import op

revision = "0062"
down_revision: str | None = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Deployment stops the API first. Preserve the oldest running job for each
    # owner and make any pre-existing sibling explicitly resumable by an operator.
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY owner_id ORDER BY created_at, id
                ) AS owner_rank
                FROM report_jobs
                WHERE status = 'running'
            )
            UPDATE report_jobs
            SET status = 'paused', lease_token = NULL, lease_until = NULL,
                error = 'interrupted_uncertain', revision = revision + 1
            WHERE id IN (SELECT id FROM ranked WHERE owner_rank > 1)
            """
        )
    )
    op.create_index(
        "uq_report_jobs_running_owner",
        "report_jobs",
        ["owner_id"],
        unique=True,
        sqlite_where=sa.text("status = 'running'"),
        postgresql_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.drop_index("uq_report_jobs_running_owner", table_name="report_jobs")
