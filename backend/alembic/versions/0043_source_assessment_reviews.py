"""Scoped reviewer policy histories and separately frozen exact-version assessments."""

import sqlalchemy as sa
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_review_heads",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id")),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("latest_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('reliability','credibility','authenticity')", name="ck_source_review_kind"
        ),
    )
    op.create_index("ix_source_review_owner", "source_review_heads", ["owner_id", "team_id"])
    op.create_table(
        "source_review_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "head_key", sa.String(64), sa.ForeignKey("source_review_heads.key"), nullable=False
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("payload_bytes", sa.Integer(), nullable=False),
        sa.CheckConstraint("number BETWEEN 1 AND 100", name="ck_source_review_number"),
        sa.CheckConstraint("payload_bytes BETWEEN 2 AND 16384", name="ck_source_review_bytes"),
    )
    op.create_index(
        "uq_source_review_number", "source_review_revisions", ["head_key", "number"], unique=True
    )
    op.create_table(
        "source_review_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "report_id", sa.Uuid(), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "report_version_id",
            sa.Uuid(),
            sa.ForeignKey("report_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("payload_bytes", sa.Integer(), nullable=False),
        sa.CheckConstraint("payload_bytes BETWEEN 2 AND 4194304", name="ck_source_snapshot_bytes"),
    )
    op.create_index(
        "ix_source_review_snapshot_version", "source_review_snapshots", ["report_version_id"]
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT COUNT(*) FROM source_review_heads")) or connection.scalar(
        sa.text("SELECT COUNT(*) FROM source_review_snapshots")
    ):
        raise RuntimeError("Cannot remove retained source review history or frozen assessments.")
    op.drop_table("source_review_snapshots")
    op.drop_table("source_review_revisions")
    op.drop_table("source_review_heads")
