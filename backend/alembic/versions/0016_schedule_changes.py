"""Opt-in research change summaries and explicit schedule-origin alerts.

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("schedules") as batch:
        batch.add_column(
            sa.Column("notify_on_change", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(sa.Column("last_change", sa.JSON(), nullable=True))
    with op.batch_alter_table("alerts") as batch:
        batch.alter_column("indicator_id", existing_type=sa.Uuid(), nullable=True)
        # Like the existing indicator reference, provenance survives origin deletion.
        batch.add_column(sa.Column("schedule_id", sa.Uuid(), nullable=True))
        batch.create_index("ix_alerts_schedule_id", ["schedule_id"])
        batch.create_check_constraint(
            "ck_alerts_one_origin",
            "(indicator_id IS NOT NULL AND schedule_id IS NULL) OR (indicator_id IS NULL AND schedule_id IS NOT NULL)",
        )


def downgrade() -> None:
    alerts = sa.table("alerts", sa.column("schedule_id", sa.Uuid()))
    if op.get_bind().scalar(
        sa.select(sa.func.count()).select_from(alerts).where(alerts.c.schedule_id.is_not(None))
    ):
        raise RuntimeError(
            "Cannot downgrade while schedule-origin alerts exist; preserve and explicitly resolve these records first."
        )
    with op.batch_alter_table("alerts") as batch:
        batch.drop_constraint("ck_alerts_one_origin", type_="check")
        batch.drop_index("ix_alerts_schedule_id")
        batch.drop_column("schedule_id")
        batch.alter_column("indicator_id", existing_type=sa.Uuid(), nullable=False)
    with op.batch_alter_table("schedules") as batch:
        batch.drop_column("last_change")
        batch.drop_column("notify_on_change")
