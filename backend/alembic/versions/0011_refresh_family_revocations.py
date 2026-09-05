"""Durable revocation markers for refresh-token families.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_family_revocations",
        sa.Column("family_id", sa.Uuid(), primary_key=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_refresh_family_revocations_revoked_at",
        "refresh_family_revocations",
        ["revoked_at"],
    )


def downgrade() -> None:
    op.drop_table("refresh_family_revocations")
