"""Track explicit activity per refresh family, granting existing families a rollout grace period."""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0092"
down_revision = "0091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    activity = op.create_table(
        "refresh_family_activity",
        sa.Column("family_id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_family_activity_user_id", "refresh_family_activity", ["user_id"])
    tokens = sa.table(
        "refresh_tokens", sa.column("family_id", sa.Uuid()), sa.column("user_id", sa.Uuid())
    )
    # Never reinterpret a historical token rotation as human activity. One server
    # migration timestamp gives every existing family the configured idle grace.
    now = datetime.now(UTC)
    op.get_bind().execute(
        activity.insert().from_select(
            ["family_id", "user_id", "last_activity_at"],
            sa.select(
                tokens.c.family_id, tokens.c.user_id, sa.literal(now, sa.DateTime(timezone=True))
            ).distinct(),
        )
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_family_activity_user_id", table_name="refresh_family_activity")
    op.drop_table("refresh_family_activity")
