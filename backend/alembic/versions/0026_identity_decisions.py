"""Report-anchored organisation identity decisions and immutable history.

Revision ID: 0026
Revises: 0025
"""

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("report_id", sa.Uuid(), sa.ForeignKey("reports.id"), nullable=False),
        sa.Column(
            "report_version_id", sa.Uuid(), sa.ForeignKey("report_versions.id"), nullable=False
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("subject", sa.String(4000), nullable=False),
        sa.Column("candidate_label", sa.String(64), nullable=False),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("latest_revision_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "report_version_id", "candidate_label", name="uq_identity_candidate_version"
        ),
    )
    for column in ("report_id", "created_by", "team_id"):
        op.create_index(f"ix_identity_decisions_{column}", "identity_decisions", [column])
    op.create_table(
        "identity_decision_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("decision_id", sa.Uuid(), sa.ForeignKey("identity_decisions.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.UniqueConstraint("decision_id", "number", name="uq_identity_revision_number"),
        sa.CheckConstraint("number > 0", name="ck_identity_revision_number"),
        sa.CheckConstraint("byte_size > 0", name="ck_identity_revision_bytes"),
    )
    op.create_index(
        "ix_identity_decision_revisions_decision_id", "identity_decision_revisions", ["decision_id"]
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM identity_decisions")) or connection.scalar(
        sa.text("SELECT count(*) FROM identity_decision_revisions")
    ):
        raise RuntimeError("Identity history remains; export/remove it before downgrade.")
    op.drop_table("identity_decision_revisions")
    op.drop_table("identity_decisions")
