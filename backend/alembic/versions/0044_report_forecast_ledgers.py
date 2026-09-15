"""Report-scoped append-only forecast and indicator ledger entries."""

import sqlalchemy as sa
from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_ledger_heads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column(
            "report_id", sa.Uuid(), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "report_version_id",
            sa.Uuid(),
            sa.ForeignKey("report_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "claim_id", sa.Uuid(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "claim_revision_id",
            sa.Uuid(),
            sa.ForeignKey("claim_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id")),
        sa.Column("source_evidence_label", sa.String(32)),
        sa.Column("source_excerpt_sha256", sa.String(64)),
        sa.Column("latest_ordinal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('forecast','indicator')", name="ck_report_ledger_kind"),
        sa.CheckConstraint(
            "(kind = 'forecast' AND source_evidence_label IS NULL AND source_excerpt_sha256 IS NULL) "
            "OR (kind = 'indicator' AND source_evidence_label IS NOT NULL "
            "AND source_excerpt_sha256 IS NOT NULL)",
            name="ck_report_ledger_source_anchor",
        ),
        sa.CheckConstraint("latest_ordinal BETWEEN 1 AND 512", name="ck_report_ledger_ordinal"),
    )
    op.create_index(
        "ix_report_ledger_version", "report_ledger_heads", ["report_version_id", "kind"]
    )
    op.create_index("ix_report_ledger_scope", "report_ledger_heads", ["owner_id", "team_id"])
    op.create_table(
        "report_ledger_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ledger_id",
            sa.Uuid(),
            sa.ForeignKey("report_ledger_heads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("entry_kind", sa.String(24), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("payload_bytes", sa.Integer(), nullable=False),
        sa.CheckConstraint("ordinal BETWEEN 1 AND 512", name="ck_report_ledger_entry_ordinal"),
        sa.CheckConstraint(
            "payload_bytes BETWEEN 2 AND 16384", name="ck_report_ledger_entry_bytes"
        ),
        sa.CheckConstraint(
            "entry_kind IN ('forecast_version','forecast_decision','indicator_version','indicator_reading')",
            name="ck_report_ledger_entry_kind",
        ),
    )
    op.create_index(
        "uq_report_ledger_entry_ordinal",
        "report_ledger_entries",
        ["ledger_id", "ordinal"],
        unique=True,
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT COUNT(*) FROM report_ledger_heads")):
        raise RuntimeError("Cannot discard retained forecast and indicator history.")
    op.drop_table("report_ledger_entries")
    op.drop_table("report_ledger_heads")
