"""Immutable report-anchored claim annotations.

Revision ID: 0025
Revises: 0024
"""

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("report_id", sa.Uuid(), sa.ForeignKey("reports.id"), nullable=False),
        sa.Column(
            "report_version_id", sa.Uuid(), sa.ForeignKey("report_versions.id"), nullable=False
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("latest_revision_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("report_id", "created_by", "team_id"):
        op.create_index(f"ix_claims_{column}", "claims", [column])
    op.create_table(
        "claim_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("claim_id", sa.Uuid(), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.UniqueConstraint("claim_id", "number", name="uq_claim_revision_number"),
        sa.CheckConstraint("number > 0", name="ck_claim_revision_number"),
        sa.CheckConstraint("byte_size > 0", name="ck_claim_revision_bytes"),
    )
    op.create_index("ix_claim_revisions_claim_id", "claim_revisions", ["claim_id"])


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM claims")) or connection.scalar(
        sa.text("SELECT count(*) FROM claim_revisions")
    ):
        raise RuntimeError("Claim history remains; export/remove it before downgrade.")
    op.drop_table("claim_revisions")
    op.drop_table("claims")
