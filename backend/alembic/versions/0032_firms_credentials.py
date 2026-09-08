"""Encrypted FIRMS configuration with expiring drafts and session-bound test proof."""

import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "firms_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("active_revision", sa.Integer(), nullable=False),
        sa.Column("active_encrypted", sa.Text(), nullable=True),
        sa.Column("draft_encrypted", sa.Text(), nullable=True),
        sa.Column("draft_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("draft_area", sa.String(100), nullable=True),
        sa.Column("test_generation", sa.Integer(), nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tested_revision", sa.Integer(), nullable=True),
        sa.Column("tested_actor", sa.Uuid(), nullable=True),
        sa.Column("tested_family", sa.Uuid(), nullable=True),
        sa.Column("tested_security_version", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    table = sa.table("firms_credentials", sa.column("id"))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table)):
        raise RuntimeError("Refusing downgrade: retained FIRMS connection configuration remains.")
    op.drop_table("firms_credentials")
