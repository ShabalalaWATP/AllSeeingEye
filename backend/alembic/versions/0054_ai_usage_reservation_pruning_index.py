"""Index finished AI reservations by period end so bounded pruning avoids a table scan."""

from alembic import op

revision = "0054"
down_revision: str | None = "0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_ai_usage_reservations_status_period_end",
        "ai_usage_reservations",
        ["status", "period_end"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_usage_reservations_status_period_end", table_name="ai_usage_reservations")
