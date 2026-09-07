"""Selected original asset reservations, byte storage and scrubbed lifecycle tombstones.

Revision ID: 0027
Revises: 0026
"""

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "original_assets",
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
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("evidence_label", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("event_id", sa.String(256), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(240), nullable=False),
        sa.Column("media_type", sa.String(160), nullable=False),
        sa.Column("permitted_use", sa.String(2000), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("uploader_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reservation_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("transitioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_family_id", sa.Uuid(), nullable=True),
        sa.Column("content", sa.LargeBinary(), nullable=True),
        sa.CheckConstraint(
            "status IN ('reserved','uploading','active','deleted','expired')",
            name="ck_original_asset_status",
        ),
        sa.CheckConstraint(
            "byte_count >= 0 AND byte_count <= 8388608", name="ck_original_asset_size"
        ),
        sa.CheckConstraint("version_number > 0", name="ck_original_asset_version"),
        sa.CheckConstraint(
            "(status = 'active' AND content IS NOT NULL "
            "AND length(content) = byte_count AND byte_count > 0) "
            "OR (status IN ('reserved','uploading') AND content IS NULL AND byte_count > 0) "
            "OR (status IN ('deleted','expired') AND content IS NULL AND byte_count = 0)",
            name="ck_original_asset_content",
        ),
    )
    for column in ("report_id", "owner_id", "team_id", "expires_at", "status"):
        op.create_index(f"ix_original_assets_{column}", "original_assets", [column])


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM original_assets")):
        raise RuntimeError("Original asset records remain; remove them before downgrade.")
    op.drop_table("original_assets")
