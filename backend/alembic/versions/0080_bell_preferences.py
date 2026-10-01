"""Per-account in-app bell preferences and alert rule mutes.

Additive only: small configuration rows removed with their account or rule. The
integrator re-chains this revision after the open work.
"""

import sqlalchemy as sa
from alembic import op

revision = "0080"
down_revision = "0079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bell_preferences",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_bell_preferences_user"),
            primary_key=True,
        ),
        sa.Column("muted_kinds", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "bell_rule_mutes",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_bell_rule_mutes_user"),
            primary_key=True,
        ),
        sa.Column(
            "indicator_id",
            sa.Uuid(),
            sa.ForeignKey("indicators.id", ondelete="CASCADE", name="fk_bell_rule_mutes_rule"),
            primary_key=True,
        ),
        sa.Column("muted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bell_rule_mutes_indicator", "bell_rule_mutes", ["indicator_id"])


def downgrade() -> None:
    # Preferences are viewing choices only; dropping them restores the default bell.
    op.drop_index("ix_bell_rule_mutes_indicator", table_name="bell_rule_mutes")
    op.drop_table("bell_rule_mutes")
    op.drop_table("bell_preferences")
