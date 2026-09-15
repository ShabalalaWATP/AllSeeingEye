"""Record board edit and removal kinds, and add per-membership read cursors."""

import sqlalchemy as sa
from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("team_board_posts") as batch:
        batch.add_column(sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("removal", sa.String(16), nullable=True))
        batch.create_check_constraint(
            "ck_board_removal", "removal IS NULL OR removal IN ('author', 'moderator')"
        )
    posts = sa.table(
        "team_board_posts",
        sa.column("text", sa.Text()),
        sa.column("removal", sa.String()),
        sa.column("deleted_at", sa.DateTime(timezone=True)),
    )
    removed = posts.c.deleted_at.is_not(None)
    op.execute(
        posts.update()
        .where(removed, posts.c.text == "[Removed by manager]")
        .values(removal="moderator", text="[Removed by a moderator]")
    )
    op.execute(posts.update().where(removed, posts.c.removal.is_(None)).values(removal="author"))
    op.create_table(
        "team_board_read_cursors",
        sa.Column(
            "team_id",
            sa.Uuid(),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("membership_joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_read_post_id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    # Read cursors are convenience state and can be rebuilt; board history is kept.
    op.drop_table("team_board_read_cursors")
    with op.batch_alter_table("team_board_posts") as batch:
        batch.drop_constraint("ck_board_removal", type_="check")
        batch.drop_column("removal")
        batch.drop_column("edited_at")
