"""Board mention recipients for the notification bell.

Additive only: at most ten small rows per post, removed with the post, recipient or
team. The integrator re-chains this revision after the open work.
"""

import sqlalchemy as sa
from alembic import op

revision = "0081"
down_revision = "0080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_board_mentions",
        sa.Column(
            "post_id",
            sa.Uuid(),
            sa.ForeignKey("team_board_posts.id", ondelete="CASCADE", name="fk_board_mentions_post"),
            primary_key=True,
        ),
        sa.Column(
            "recipient_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_board_mentions_recipient"),
            primary_key=True,
        ),
        sa.Column(
            "team_id",
            sa.Uuid(),
            sa.ForeignKey("teams.id", ondelete="CASCADE", name="fk_board_mentions_team"),
            nullable=False,
        ),
        sa.Column("handle", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("post_id", "handle", name="uq_board_mention_handle"),
    )
    op.create_index(
        "ix_board_mentions_recipient", "team_board_mentions", ["recipient_id", "read_at"]
    )


def downgrade() -> None:
    # Posts keep their text; only the derived notices are dropped.
    op.drop_index("ix_board_mentions_recipient", table_name="team_board_mentions")
    op.drop_table("team_board_mentions")
