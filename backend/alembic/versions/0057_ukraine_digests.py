"""Store the last few fortnightly Ukraine digests with their provenance."""

import sqlalchemy as sa
from alembic import op

revision = "0057"
down_revision: str | None = "0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ukraine_digests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model", sa.String(2048), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("source_ids", sa.JSON(), nullable=False),
        sa.Column("evidence_items", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
    )
    op.create_index("ix_ukraine_digests_generated_at", "ukraine_digests", ["generated_at"])


def downgrade() -> None:
    op.drop_index("ix_ukraine_digests_generated_at", table_name="ukraine_digests")
    op.drop_table("ukraine_digests")
