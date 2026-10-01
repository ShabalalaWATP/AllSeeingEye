"""Opt-in rule ratios and the frozen baseline values of a firing."""

import sqlalchemy as sa
from alembic import op

revision = "0085"
down_revision = "0084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("indicators", sa.Column("baseline_ratio", sa.Float(), nullable=True))
    op.add_column(
        "indicators", sa.Column("baseline_days", sa.Integer(), nullable=False, server_default="30")
    )
    op.add_column("alerts", sa.Column("baseline_mean", sa.Float(), nullable=True))
    op.add_column("alerts", sa.Column("baseline_ratio", sa.Float(), nullable=True))


def downgrade() -> None:
    rules = sa.table("indicators", sa.column("baseline_ratio"))
    if (
        op.get_bind()
        .execute(
            sa.select(rules.c.baseline_ratio).where(rules.c.baseline_ratio.is_not(None)).limit(1)
        )
        .first()
    ):
        raise RuntimeError("Remove ratio rules explicitly before downgrade.")
    # Fired evidence survives changing a rule back to absolute mode or deleting it.
    alerts = sa.table("alerts", sa.column("baseline_mean"), sa.column("baseline_ratio"))
    if (
        op.get_bind()
        .execute(
            sa.select(alerts.c.baseline_mean)
            .where(
                sa.or_(alerts.c.baseline_mean.is_not(None), alerts.c.baseline_ratio.is_not(None))
            )
            .limit(1)
        )
        .first()
    ):
        raise RuntimeError("Refusing downgrade: retained alert baseline evidence remains.")
    op.drop_column("alerts", "baseline_ratio")
    op.drop_column("alerts", "baseline_mean")
    op.drop_column("indicators", "baseline_days")
    op.drop_column("indicators", "baseline_ratio")
