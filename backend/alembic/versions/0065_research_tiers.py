"""Per-user research levels and durable calendar-period usage."""

import sqlalchemy as sa
from alembic import op

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Missing assignments mean Level 1 for existing and future accounts alike.
    op.create_table(
        "research_tiers",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.CheckConstraint("tier BETWEEN 1 AND 4", name="ck_research_tier"),
        sa.CheckConstraint("revision > 0", name="ck_research_tier_revision"),
    )
    op.create_table(
        "research_usage",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("period", sa.String(4), primary_key=True),
        sa.Column("period_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("used", sa.Integer(), nullable=False),
        sa.CheckConstraint("period IN ('day', 'week')", name="ck_research_usage_period"),
        sa.CheckConstraint("used >= 0", name="ck_research_usage_used"),
    )


def downgrade() -> None:
    connection = op.get_bind()
    for table_name in ("research_usage", "research_tiers"):
        table = sa.table(table_name, sa.column("user_id"))
        if connection.execute(sa.select(table.c.user_id).limit(1)).first():
            raise RuntimeError("Cannot downgrade while research allowance records remain.")
    op.drop_table("research_usage")
    op.drop_table("research_tiers")
