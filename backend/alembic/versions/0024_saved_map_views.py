"""Immutable report-anchored saved map revisions.

Revision ID: 0024
Revises: 0023
"""

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "map_views",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("report_id", sa.Uuid(), sa.ForeignKey("reports.id"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("latest_revision_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
    )
    for column in ("report_id", "created_by", "team_id"):
        op.create_index(f"ix_map_views_{column}", "map_views", [column])
    op.create_table(
        "map_view_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("view_id", sa.Uuid(), sa.ForeignKey("map_views.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "report_version_id", sa.Uuid(), sa.ForeignKey("report_versions.id"), nullable=False
        ),
        sa.Column("report_version_number", sa.Integer(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("view_id", "number", name="uq_map_view_revision_number"),
        sa.CheckConstraint("number > 0", name="ck_map_view_revision_number"),
        sa.CheckConstraint("byte_size > 0", name="ck_map_view_revision_bytes"),
    )
    op.create_index("ix_map_view_revisions_view_id", "map_view_revisions", ["view_id"])


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM map_views")) or connection.scalar(
        sa.text("SELECT count(*) FROM map_view_revisions")
    ):
        raise RuntimeError("Saved map revisions remain; export/remove them before downgrade.")
    op.drop_table("map_view_revisions")
    op.drop_table("map_views")
