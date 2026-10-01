"""Provenance for team copies of finished personal report versions.

Additive only. The integrator re-chains this revision after the open work.
"""

import sqlalchemy as sa
from alembic import op

revision = "0078"
down_revision = "0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_team_copies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "report_id",
            sa.Uuid(),
            sa.ForeignKey("reports.id", ondelete="CASCADE", name="fk_report_team_copies_report"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            sa.Uuid(),
            sa.ForeignKey("teams.id", name="fk_report_team_copies_team"),
            nullable=False,
        ),
        sa.Column("source_report_id", sa.Uuid(), nullable=False),
        sa.Column("source_version_id", sa.Uuid(), nullable=False),
        sa.Column("source_version_number", sa.Integer(), nullable=False),
        sa.Column(
            "copied_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", name="fk_report_team_copies_user"),
            nullable=False,
        ),
        sa.Column("copied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("disclosed_labels", sa.JSON(), nullable=False),
        sa.Column("omissions", sa.JSON(), nullable=False),
        sa.UniqueConstraint("source_version_id", "team_id", name="uq_report_team_copy_source"),
        sa.UniqueConstraint("report_id", name="uq_report_team_copy_report"),
        sa.CheckConstraint("source_version_number >= 1", name="ck_report_team_copy_version"),
    )
    op.create_index("ix_report_team_copies_source", "report_team_copies", ["source_report_id"])


def downgrade() -> None:
    # Copied team reports remain ordinary team reports; only their provenance is dropped.
    op.drop_index("ix_report_team_copies_source", table_name="report_team_copies")
    op.drop_table("report_team_copies")
