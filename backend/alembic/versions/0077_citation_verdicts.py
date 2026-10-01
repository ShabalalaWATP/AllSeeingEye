"""Append-only human citation verdicts anchored to exact saved report versions (KAN-114).

Additive: one new table. Downgrade drops it, which discards recorded verdicts only.
"""

import sqlalchemy as sa
from alembic import op

revision = "0077"
down_revision = "0076"
branch_labels = None
depends_on = None

# Kept literal so later model edits cannot rewrite this historical migration.
CHECKS = (
    (
        "verdict IN ('supports','partly_supports','does_not_support','cannot_tell')",
        "ck_citation_verdicts_verdict",
    ),
    ("relation IN ('supporting','contradicting')", "ck_citation_verdicts_relation"),
    ("note IS NULL OR length(note) BETWEEN 1 AND 300", "ck_citation_verdicts_note"),
    ("version_number >= 1", "ck_citation_verdicts_version"),
)


def upgrade() -> None:
    op.create_table(
        "citation_verdicts",
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
        sa.Column("judgement_id", sa.String(200), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("relation", sa.String(16), nullable=False),
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("reviewer_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        *(sa.CheckConstraint(sql, name=name) for sql, name in CHECKS),
    )
    op.create_index(
        "ix_citation_verdicts_version", "citation_verdicts", ["report_version_id", "recorded_at"]
    )
    op.create_index("ix_citation_verdicts_scope", "citation_verdicts", ["owner_id", "team_id"])
    op.create_index("ix_citation_verdicts_recorded_at", "citation_verdicts", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_citation_verdicts_recorded_at", table_name="citation_verdicts")
    op.drop_index("ix_citation_verdicts_scope", table_name="citation_verdicts")
    op.drop_index("ix_citation_verdicts_version", table_name="citation_verdicts")
    op.drop_table("citation_verdicts")
