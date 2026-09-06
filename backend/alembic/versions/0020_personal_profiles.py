"""Private profile preferences.

Revision ID: 0020
Revises: 0019
"""

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "personal_profiles",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("preferences", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("personal_profiles")
