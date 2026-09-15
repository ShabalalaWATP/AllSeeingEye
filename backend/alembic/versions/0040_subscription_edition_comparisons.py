"""Persist immutable, exact-version subscription edition comparisons."""

import sqlalchemy as sa
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_edition_comparisons",
        sa.Column(
            "edition_id", sa.Uuid(), sa.ForeignKey("subscription_editions.id"), primary_key=True
        ),
        sa.Column(
            "previous_version_id", sa.Uuid(), sa.ForeignKey("report_versions.id"), nullable=True
        ),
        sa.Column(
            "current_version_id", sa.Uuid(), sa.ForeignKey("report_versions.id"), nullable=False
        ),
        sa.Column("state", sa.String(64), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('failure','insufficient_coverage',"
            "'significant_contradiction_or_correction','assessment_changed',"
            "'new_evidence_broadly_unchanged_assessment',"
            "'no_new_relevant_captured_evidence')",
            name="ck_subscription_comparison_state",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    retained = bind.execute(
        sa.text("SELECT 1 FROM subscription_edition_comparisons LIMIT 1")
    ).first()
    if retained is not None:
        raise RuntimeError("Downgrade would remove retained subscription comparison history.")
    op.drop_table("subscription_edition_comparisons")
