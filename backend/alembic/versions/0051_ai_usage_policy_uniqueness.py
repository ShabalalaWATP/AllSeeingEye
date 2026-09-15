"""Prevent duplicate AI allowance targets under concurrent administration."""

import sqlalchemy as sa
from alembic import op

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NULL values do not compare equal in a normal unique index, so the site and
    # system policies need their own partial index, unique per scope. User and
    # team targets share the second index and are unique within their scope.
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


def downgrade() -> None:
    op.drop_index("uq_ai_usage_policy_target", table_name="ai_usage_policies")
    op.drop_index("uq_ai_usage_policy_global", table_name="ai_usage_policies")
