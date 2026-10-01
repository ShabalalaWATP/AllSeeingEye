"""Let a top-level board post name one team report version, saved area or drawing collection."""

import sqlalchemy as sa
from alembic import op

revision = "0075"
down_revision = "0066"
branch_labels = None
depends_on = None

# Kept literal so later model changes never rewrite this revision.
SUBJECT_SHAPE = (
    "(subject_kind IS NULL AND subject_id IS NULL AND subject_version IS NULL)"
    " OR (subject_kind IS NOT NULL AND subject_id IS NOT NULL AND parent_id IS NULL AND ("
    "(subject_kind = 'report_version' AND subject_version IS NOT NULL AND subject_version >= 1)"
    " OR (subject_kind IN ('saved_area', 'drawing_collection') AND subject_version IS NULL)))"
)


def upgrade() -> None:
    # Batch mode recreates the SQLite table and uses ALTER TABLE on PostgreSQL. Existing
    # posts keep no subject, so the change is additive.
    with op.batch_alter_table("team_board_posts") as batch:
        batch.add_column(sa.Column("subject_kind", sa.String(24), nullable=True))
        batch.add_column(sa.Column("subject_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("subject_version", sa.Integer(), nullable=True))
        batch.create_check_constraint("ck_board_subject", SUBJECT_SHAPE)
        batch.create_index("ix_team_board_posts_subject", ["team_id", "subject_kind", "subject_id"])


def downgrade() -> None:
    # The posts and their text stay; only the optional typed references are dropped.
    with op.batch_alter_table("team_board_posts") as batch:
        batch.drop_index("ix_team_board_posts_subject")
        batch.drop_constraint("ck_board_subject", type_="check")
        batch.drop_column("subject_version")
        batch.drop_column("subject_id")
        batch.drop_column("subject_kind")
