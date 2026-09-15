"""Tombstone subscriptions without deleting immutable editions or selected-index children."""

import sqlalchemy as sa
from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("schedules", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    connection = op.get_bind()
    archived = connection.scalar(
        sa.text("SELECT COUNT(*) FROM schedules WHERE archived_at IS NOT NULL")
    )
    if archived:
        raise RuntimeError("Cannot remove subscription tombstones while archived history remains.")
    op.drop_column("schedules", "archived_at")
