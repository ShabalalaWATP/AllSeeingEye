"""Retain exact selected public excerpts only until their reviewed source policy expiry."""

import sqlalchemy as sa
from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "original_passage_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "job_id", sa.Uuid(), sa.ForeignKey("report_jobs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "report_version_id",
            sa.Uuid(),
            sa.ForeignKey("report_versions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("event_id", sa.String(256), nullable=False),
        sa.Column("evidence_label", sa.String(16), nullable=False),
        sa.Column("candidate_id", sa.String(64), nullable=False),
        sa.Column("document_version_id", sa.String(64), nullable=False),
        sa.Column("passage_id", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("snapshot_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(document_version_id) = 64", name="ck_original_passage_version"),
        sa.CheckConstraint("length(passage_id) = 64", name="ck_original_passage_digest"),
    )
    op.create_index(
        "ix_original_passage_job_event",
        "original_passage_assets",
        ["job_id", "event_id"],
        unique=True,
    )
    op.create_index("ix_original_passage_expiry", "original_passage_assets", ["expires_at"])
    op.create_index(
        "ix_original_passage_assets_report_version_id",
        "original_passage_assets",
        ["report_version_id"],
    )
    op.create_index("ix_original_passage_assets_owner_id", "original_passage_assets", ["owner_id"])


def downgrade() -> None:
    retained = (
        op.get_bind().execute(sa.text("SELECT 1 FROM original_passage_assets LIMIT 1")).first()
    )
    if retained is not None:
        raise RuntimeError("Downgrade would remove retained original passages.")
    op.drop_index("ix_original_passage_assets_owner_id", table_name="original_passage_assets")
    op.drop_index(
        "ix_original_passage_assets_report_version_id", table_name="original_passage_assets"
    )
    op.drop_index("ix_original_passage_expiry", table_name="original_passage_assets")
    op.drop_index("ix_original_passage_job_event", table_name="original_passage_assets")
    op.drop_table("original_passage_assets")
