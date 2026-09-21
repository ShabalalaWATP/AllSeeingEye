"""Allow Level 5 without changing existing assignments or research usage."""

import sqlalchemy as sa
from alembic import op

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def _tier_constraint(maximum: int) -> None:
    # Batch mode recreates the SQLite table and uses ALTER TABLE on PostgreSQL.
    with op.batch_alter_table("research_tiers") as batch:
        batch.drop_constraint("ck_research_tier", type_="check")
        batch.create_check_constraint("ck_research_tier", f"tier BETWEEN 1 AND {maximum}")


def upgrade() -> None:
    _tier_constraint(5)


def downgrade() -> None:
    tiers = sa.table("research_tiers", sa.column("tier"))
    if op.get_bind().execute(sa.select(tiers.c.tier).where(tiers.c.tier == 5).limit(1)).first():
        raise RuntimeError("Reassign Level 5 users before downgrading the research tier migration.")
    _tier_constraint(4)
