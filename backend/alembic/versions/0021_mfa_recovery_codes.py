"""Single-use MFA recovery hashes.

Revision ID: 0021
Revises: 0020
"""

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mfa_recovery_codes",
        sa.Column("code_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("security_version", sa.Integer(), nullable=False),
    )
    op.create_index("ix_mfa_recovery_codes_user_id", "mfa_recovery_codes", ["user_id"])


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM mfa_recovery_codes")):
        raise RuntimeError("Recovery codes remain configured; invalidate them before downgrade.")
    op.drop_index("ix_mfa_recovery_codes_user_id", table_name="mfa_recovery_codes")
    op.drop_table("mfa_recovery_codes")
