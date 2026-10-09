"""Retain bounded triggering evidence for exact alert reports, without historical replay."""

import sqlalchemy as sa
from alembic import op

revision = "0091"
down_revision = "0090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("report_snapshot", sa.JSON(), nullable=True))
    # Legacy pending intents lack the evidence needed to honour their original scope.
    op.execute(
        sa.text(
            "UPDATE alerts SET report_status = 'failed', report_error = 'evidence_unavailable', "
            "report_next_attempt_at = NULL WHERE report_status = 'pending'"
        )
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text("SELECT COUNT(*) FROM alerts WHERE report_snapshot IS NOT NULL")
    ):
        raise RuntimeError("Cannot downgrade while frozen alert report evidence is retained.")
    with op.batch_alter_table("alerts") as batch:
        batch.drop_column("report_snapshot")
