"""Persist IANA wall-clock recurrence and collection policy for subscriptions."""

import sqlalchemy as sa
from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("schedules") as batch:
        batch.add_column(
            sa.Column("timezone", sa.String(100), nullable=False, server_default="UTC")
        )
        batch.add_column(sa.Column("local_hour", sa.Integer(), nullable=False, server_default="6"))
        batch.add_column(
            sa.Column("local_minute", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column(
                "collection_policy",
                sa.String(32),
                nullable=False,
                server_default="rolling_snapshot",
            )
        )
    op.execute(sa.text("UPDATE schedules SET local_hour = hour_utc"))
    with op.batch_alter_table("subscription_editions") as batch:
        batch.add_column(sa.Column("covered_by_edition_id", sa.Uuid(), nullable=True))


def downgrade() -> None:
    connection = op.get_bind()
    if (
        connection.execute(
            sa.text(
                "SELECT 1 FROM subscription_editions WHERE covered_by_edition_id IS NOT NULL LIMIT 1"
            )
        ).first()
        is not None
    ):
        raise RuntimeError("Downgrade would lose subscription catch-up history.")
    changed = connection.execute(
        sa.text(
            "SELECT 1 FROM schedules WHERE timezone <> 'UTC' "
            "OR local_hour <> hour_utc OR local_minute <> 0 "
            "OR collection_policy <> 'rolling_snapshot' LIMIT 1"
        )
    ).first()
    if changed is not None:
        raise RuntimeError("Downgrade would lose active local subscription settings.")
    with op.batch_alter_table("schedules") as batch:
        batch.drop_column("collection_policy")
        batch.drop_column("local_minute")
        batch.drop_column("local_hour")
        batch.drop_column("timezone")
    with op.batch_alter_table("subscription_editions") as batch:
        batch.drop_column("covered_by_edition_id")
