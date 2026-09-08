"""Exact-version inventory subscriptions with bounded durable overflow state."""

import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("annotation_monitors") as batch:
        batch.add_column(
            sa.Column("mode", sa.String(24), nullable=False, server_default="selected_roots")
        )
        batch.add_column(
            sa.Column("inventory_overflow", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    with op.batch_alter_table("annotation_revision_outbox") as batch:
        batch.alter_column("previous_revision_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    connection = op.get_bind()
    monitors = sa.table("annotation_monitors", sa.column("mode"), sa.column("inventory_overflow"))
    events = sa.table("annotation_revision_outbox", sa.column("previous_revision_id"))
    unsafe_monitor = connection.scalar(
        sa.select(sa.func.count())
        .select_from(monitors)
        .where(sa.or_(monitors.c.mode != "selected_roots", monitors.c.inventory_overflow.is_(True)))
    )
    creations = connection.scalar(
        sa.select(sa.func.count())
        .select_from(events)
        .where(events.c.previous_revision_id.is_(None))
    )
    if unsafe_monitor or creations:
        raise RuntimeError(
            "Refusing downgrade: inventory subscriptions or creation history remain."
        )
    with op.batch_alter_table("annotation_revision_outbox") as batch:
        batch.alter_column("previous_revision_id", existing_type=sa.Uuid(), nullable=False)
    with op.batch_alter_table("annotation_monitors") as batch:
        batch.drop_column("inventory_overflow")
        batch.drop_column("mode")
