"""Preserve canonical geometry and its hash for saved areas and warning rules."""

import sqlalchemy as sa
from alembic import op

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing rectangles and nation records retain their semantics unchanged.
    op.add_column("aois", sa.Column("research_area", sa.JSON(), nullable=True))
    op.add_column("indicators", sa.Column("research_area", sa.JSON(), nullable=True))


def downgrade() -> None:
    # An exact area cannot become a rectangle silently on rollback.
    connection = op.get_bind()
    for table in ("aois", "indicators"):
        rows = sa.table(table, sa.column("research_area"))
        if connection.execute(
            sa.select(rows.c.research_area).where(rows.c.research_area.is_not(None)).limit(1)
        ).first():
            raise RuntimeError("Remove exact areas explicitly before downgrading this migration.")
    op.drop_column("indicators", "research_area")
    op.drop_column("aois", "research_area")
