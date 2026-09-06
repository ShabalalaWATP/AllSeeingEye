"""Preserve saved questions and bounded research configuration for schedules.

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("schedules") as batch:
        batch.add_column(sa.Column("question", sa.String(1000), nullable=True))
        batch.add_column(sa.Column("research_options", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("schedules") as batch:
        batch.drop_column("research_options")
        batch.drop_column("question")
