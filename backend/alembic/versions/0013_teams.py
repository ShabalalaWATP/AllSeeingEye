"""Explicit teams and memberships, without assigning existing records or users.

Revision ID: 0013
Revises: 0012
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "team_memberships",
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('member', 'manager')", name="ck_membership_role"),
    )
    op.create_index("ix_team_memberships_user_id", "team_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_table("team_memberships")
    op.drop_table("teams")
