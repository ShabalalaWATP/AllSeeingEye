"""Bounded vectors for semantic search of current saved reports.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_embeddings",
        sa.Column(
            "report_id",
            sa.Uuid(),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("report_embeddings")
