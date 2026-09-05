"""Optional administrator TOTP secrets and atomic replay protection.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_totp",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("secret_encrypted", sa.String(2048), nullable=True),
        sa.Column("pending_encrypted", sa.String(2048), nullable=True),
        sa.Column("pending_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_step", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("admin_totp")
