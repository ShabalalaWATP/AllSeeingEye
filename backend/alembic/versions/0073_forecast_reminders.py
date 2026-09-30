"""One in-app review reminder receipt per forecast version and review date."""

import sqlalchemy as sa
from alembic import op

revision = "0073"
down_revision = "0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_review_reminders",
        sa.Column("version_id", sa.Uuid(), primary_key=True),
        sa.Column("review_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column(
            "ledger_id",
            sa.Uuid(),
            sa.ForeignKey("report_ledger_heads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reminded_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("forecast_review_reminders")
