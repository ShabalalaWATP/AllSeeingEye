"""Personal report library, separate from report content and scope.

Revision ID: 0023
Revises: 0022
"""

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_library",
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "report_id",
            sa.Uuid(),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("favourite", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "research_library_tags",
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column("report_id", sa.Uuid(), primary_key=True),
        sa.Column("tag", sa.String(40), primary_key=True),
        sa.ForeignKeyConstraint(
            ["user_id", "report_id"],
            ["research_library.user_id", "research_library.report_id"],
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM research_library")):
        raise RuntimeError("Library entries remain; export/remove them before downgrade.")
    op.drop_table("research_library_tags")
    op.drop_table("research_library")
