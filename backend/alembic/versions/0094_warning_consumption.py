"""Bound consumed warning identities independently of displayed citations."""

import sqlalchemy as sa
from alembic import op

revision = "0094"
down_revision = "0093"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "warning_consumption",
        sa.Column(
            "indicator_id",
            sa.Uuid(),
            sa.ForeignKey("indicators.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legacy_before", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("count >= 0 AND count <= 350000", name="ck_warning_consumed_count"),
    )
    op.create_index("ix_warning_consumption_expires_at", "warning_consumption", ["expires_at"])
    # Old alerts never retained all consumed IDs. Mark that ambiguity explicitly;
    # do not invent a complete consumed set from their twenty displayed citations.
    op.get_bind().execute(
        sa.text(
            "INSERT INTO warning_consumption (indicator_id, data, count, expires_at, legacy_before) "
            "SELECT i.id, :empty, 0, NULL, MAX(a.fired_at) FROM indicators i JOIN alerts a "
            "ON a.indicator_id = i.id AND a.created_by = i.created_by "
            "AND (a.team_id = i.team_id OR (a.team_id IS NULL AND i.team_id IS NULL)) "
            "GROUP BY i.id"
        ),
        {"empty": b"ASEC\x01"},
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM warning_consumption")):
        raise RuntimeError("Cannot downgrade while consumed warning evidence is retained.")
    op.drop_table("warning_consumption")
