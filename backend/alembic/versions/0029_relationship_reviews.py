"""Report-anchored organisation relationship decisions and immutable history.

Revision ID: 0029
Revises: 0028
"""

import sqlalchemy as sa
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "relationship_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("report_id", sa.Uuid(), sa.ForeignKey("reports.id"), nullable=False),
        sa.Column(
            "report_version_id", sa.Uuid(), sa.ForeignKey("report_versions.id"), nullable=False
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("evidence_label", sa.String(64), nullable=False),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("latest_revision_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "report_version_id", "evidence_label", name="uq_relationship_assertion_version"
        ),
    )
    for column in ("report_id", "created_by", "team_id"):
        op.create_index(f"ix_relationship_reviews_{column}", "relationship_reviews", [column])
    op.create_table(
        "relationship_review_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "relationship_id", sa.Uuid(), sa.ForeignKey("relationship_reviews.id"), nullable=False
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.UniqueConstraint("relationship_id", "number", name="uq_relationship_revision_number"),
        sa.CheckConstraint("number > 0", name="ck_relationship_revision_number"),
        sa.CheckConstraint("byte_size > 0", name="ck_relationship_revision_bytes"),
    )
    op.create_index(
        "ix_relationship_review_revisions_relationship_id",
        "relationship_review_revisions",
        ["relationship_id"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM relationship_reviews")) or connection.scalar(
        sa.text("SELECT count(*) FROM relationship_review_revisions")
    ):
        raise RuntimeError("Relationship history remains; export/remove it before downgrade.")
    op.drop_table("relationship_review_revisions")
    op.drop_table("relationship_reviews")
