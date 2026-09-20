"""Bounded personal/team drawings and radio study documents."""

import sqlalchemy as sa
from alembic import op

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "map_workspace_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision > 0", name="ck_map_workspace_revision"),
    )
    op.create_index(
        "ix_map_workspace_documents_created_by", "map_workspace_documents", ["created_by"]
    )
    op.create_index("ix_map_workspace_documents_team_id", "map_workspace_documents", ["team_id"])


def downgrade() -> None:
    op.drop_table("map_workspace_documents")
