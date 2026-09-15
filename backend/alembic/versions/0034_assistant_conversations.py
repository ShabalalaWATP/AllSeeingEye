"""Private bounded Ask Eye snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("transcript_bytes", sa.Integer(), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "transcript_bytes BETWEEN 2 AND 65536", name="ck_assistant_transcript_size"
        ),
        sa.CheckConstraint("turn_count BETWEEN 1 AND 8", name="ck_assistant_turn_count"),
    )
    op.create_index(
        "ix_assistant_conversations_owner_updated",
        "assistant_conversations",
        ["owner_id", "updated_at", "id"],
    )


def downgrade() -> None:
    table = sa.table("assistant_conversations", sa.column("id"))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table)):
        raise RuntimeError("Refusing downgrade: saved conversations remain.")
    op.drop_index("ix_assistant_conversations_owner_updated", table_name="assistant_conversations")
    op.drop_table("assistant_conversations")
