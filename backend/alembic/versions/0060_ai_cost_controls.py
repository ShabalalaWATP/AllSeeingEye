"""Split observed AI tokens by direction and allow one allowance per target per period.

Two changes, both needed before an administrator can control cost rather than only
observe it.  Totals gain an input/output split so recorded tokens can be priced, and the
policy uniqueness indexes gain ``period`` so a target can carry a daily and a monthly
cap at the same time instead of only one.
"""

import sqlalchemy as sa
from alembic import op

revision = "0060"
down_revision: str | None = "0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_usage_totals",
        sa.Column("used_input_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "ai_usage_totals",
        sa.Column("used_output_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    # History recorded before this migration has no split. Counting it all as output
    # keeps the sum equal to used_tokens and never understates an estimate.
    op.execute(sa.text("UPDATE ai_usage_totals SET used_output_tokens = used_tokens"))
    op.drop_index("uq_ai_usage_policy_target", table_name="ai_usage_policies")
    op.drop_index("uq_ai_usage_policy_global", table_name="ai_usage_policies")
    op.create_index(
        "uq_ai_usage_policy_global",
        "ai_usage_policies",
        ["scope", "period"],
        unique=True,
        sqlite_where=sa.text("scope IN ('global','system') AND enabled = 1"),
        postgresql_where=sa.text("scope IN ('global','system') AND enabled = true"),
    )
    op.create_index(
        "uq_ai_usage_policy_target",
        "ai_usage_policies",
        ["scope", "target_id", "period"],
        unique=True,
        sqlite_where=sa.text("scope IN ('user','team') AND enabled = 1"),
        postgresql_where=sa.text("scope IN ('user','team') AND enabled = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_ai_usage_policy_target", table_name="ai_usage_policies")
    op.drop_index("uq_ai_usage_policy_global", table_name="ai_usage_policies")
    op.create_index(
        "uq_ai_usage_policy_global",
        "ai_usage_policies",
        ["scope"],
        unique=True,
        sqlite_where=sa.text("scope IN ('global','system') AND enabled = 1"),
        postgresql_where=sa.text("scope IN ('global','system') AND enabled = true"),
    )
    op.create_index(
        "uq_ai_usage_policy_target",
        "ai_usage_policies",
        ["scope", "target_id"],
        unique=True,
        sqlite_where=sa.text("scope IN ('user','team') AND enabled = 1"),
        postgresql_where=sa.text("scope IN ('user','team') AND enabled = true"),
    )
    op.drop_column("ai_usage_totals", "used_output_tokens")
    op.drop_column("ai_usage_totals", "used_input_tokens")
