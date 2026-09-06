"""Account MFA and explicit assurance on refresh sessions.

Revision ID: 0019
Revises: 0018
"""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.add_column(
            sa.Column("mfa_verified", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    op.create_table(
        "email_mfa",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "mfa_challenges",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("security_version", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("enrollment_required", sa.Boolean(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(512), nullable=True),
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pending_encrypted", sa.String(2048), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mfa_challenges_user_id", "mfa_challenges", ["user_id"])
    op.create_index("ix_mfa_challenges_expires_at", "mfa_challenges", ["expires_at"])


def downgrade() -> None:
    connection = op.get_bind()
    email = sa.table("email_mfa", sa.column("enabled", sa.Boolean()))
    if connection.scalar(sa.select(sa.func.count()).select_from(email).where(email.c.enabled)):
        raise RuntimeError("Cannot downgrade while email MFA is enabled.")
    # The previous application permits password-only administrators and ignores
    # ordinary users' TOTP. Retain the stronger policy until explicitly reviewed.
    factors = sa.table("admin_totp", sa.column("secret_encrypted", sa.String()))
    if connection.scalar(
        sa.select(sa.func.count())
        .select_from(factors)
        .where(factors.c.secret_encrypted.is_not(None))
    ):
        raise RuntimeError("Cannot downgrade while authenticator MFA is configured.")
    op.drop_table("mfa_challenges")
    op.drop_table("email_mfa")
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.drop_column("mfa_verified")
