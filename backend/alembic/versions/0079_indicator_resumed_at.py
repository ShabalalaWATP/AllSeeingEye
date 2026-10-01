"""When an alert rule was last resumed, so a resumed rule never replays its paused period.

Additive only: a nullable column. Existing rules keep counting their whole window.
"""

import sqlalchemy as sa
from alembic import op

revision = "0079"
down_revision = "0078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("indicators") as batch:
        batch.add_column(sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Resumed rules then count their whole window again; no rule or alert is removed.
    with op.batch_alter_table("indicators") as batch:
        batch.drop_column("resumed_at")
