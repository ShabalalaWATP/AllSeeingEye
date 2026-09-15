"""Add the bounded plain-text team board."""

import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_board_posts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "team_id", sa.Uuid(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "parent_id",
            sa.Uuid(),
            sa.ForeignKey("team_board_posts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("length(text) BETWEEN 1 AND 4000", name="ck_board_text_length"),
        sa.CheckConstraint(
            "parent_id IS NULL OR length(text) BETWEEN 1 AND 2000",
            name="ck_board_reply_text_length",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_board_revision"),
    )
    op.create_index("ix_team_board_posts_team", "team_board_posts", ["team_id"])
    op.create_index("ix_team_board_posts_author", "team_board_posts", ["author_id"])
    op.create_index("ix_team_board_posts_created", "team_board_posts", ["team_id", "created_at"])
    op.create_index("ix_team_board_posts_parent", "team_board_posts", ["parent_id"])
    op.create_index("ix_team_board_posts_pinned", "team_board_posts", ["team_id", "is_pinned"])


def downgrade() -> None:
    table = sa.table("team_board_posts", sa.column("id"))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table)):
        raise RuntimeError("Refusing downgrade: team board posts remain.")
    for name in (
        "ix_team_board_posts_pinned",
        "ix_team_board_posts_parent",
        "ix_team_board_posts_created",
        "ix_team_board_posts_author",
        "ix_team_board_posts_team",
    ):
        op.drop_index(name, table_name="team_board_posts")
    op.drop_table("team_board_posts")
