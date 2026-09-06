"""Authoritative access-session security versions and administrator transition lock.

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("security_version", sa.Integer(), nullable=False, server_default="0")
    )
    op.create_table("administration_lock", sa.Column("id", sa.Integer(), primary_key=True))


def downgrade() -> None:
    op.drop_table("administration_lock")
    op.drop_column("users", "security_version")
