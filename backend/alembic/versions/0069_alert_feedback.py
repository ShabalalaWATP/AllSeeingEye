"""Optional shared alert dispositions and minimum daily aggregate retention."""

import sqlalchemy as sa
from alembic import op

revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("disposition", sa.String(12), nullable=True))
    op.add_column("alerts", sa.Column("disposition_note", sa.String(200), nullable=True))
    op.create_table(
        "alert_feedback_days",
        sa.Column("indicator_id", sa.Uuid(), primary_key=True),
        sa.Column("day", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("disposition", sa.String(12), primary_key=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.CheckConstraint("count >= 1", name="ck_alert_feedback_count"),
        sa.CheckConstraint(
            "disposition IN ('useful', 'noise', 'duplicate')", name="ck_alert_feedback_disposition"
        ),
    )
    op.create_index("ix_alert_feedback_days_day", "alert_feedback_days", ["day"])


def downgrade() -> None:
    table = sa.table("alert_feedback_days", sa.column("count"))
    alerts = sa.table("alerts", sa.column("disposition"), sa.column("disposition_note"))
    connection = op.get_bind()
    if (
        connection.execute(sa.select(table.c.count).limit(1)).first()
        or connection.execute(
            sa.select(alerts.c.disposition)
            .where(
                sa.or_(alerts.c.disposition.is_not(None), alerts.c.disposition_note.is_not(None))
            )
            .limit(1)
        ).first()
    ):
        raise RuntimeError("Remove retained alert feedback explicitly before downgrade.")
    op.drop_table("alert_feedback_days")
    op.drop_column("alerts", "disposition_note")
    op.drop_column("alerts", "disposition")
