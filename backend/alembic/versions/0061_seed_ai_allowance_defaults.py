"""Seed protective AI allowance defaults on installations with no policy history."""

from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision = "0061"
down_revision: str | None = "0060"
branch_labels = None
depends_on = None

_SEEDED_IDS = (
    UUID("5db95452-69b1-4d27-a921-5a9c858b0a61"),
    UUID("cb3acb85-3586-4ec5-bcf3-0bcc5fcd576a"),
    UUID("d6638db7-f772-4fb1-b0c0-797c36a31d2c"),
)


def upgrade() -> None:
    bind = op.get_bind()
    policies = sa.table(
        "ai_usage_policies",
        sa.column("id", sa.Uuid()),
        sa.column("scope", sa.String()),
        sa.column("target_id", sa.Uuid()),
        sa.column("period", sa.String()),
        sa.column("request_limit", sa.Integer()),
        sa.column("token_limit", sa.Integer()),
        sa.column("enabled", sa.Boolean()),
        sa.column("revision", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    if bind.scalar(sa.select(sa.func.count()).select_from(policies)):
        return
    now = datetime.now(UTC)
    op.bulk_insert(
        policies,
        [
            _row(_SEEDED_IDS[0], "global", "day", 300_000, now),
            _row(_SEEDED_IDS[1], "global", "month", 9_000_000, now),
            _row(_SEEDED_IDS[2], "system", "day", 100_000, now),
        ],
    )


def _row(
    policy_id: UUID, scope: str, period: str, token_limit: int, now: datetime
) -> dict[str, object]:
    return {
        "id": policy_id,
        "scope": scope,
        "target_id": None,
        "period": period,
        "request_limit": None,
        "token_limit": token_limit,
        "enabled": True,
        "revision": 1,
        "created_at": now,
        "updated_at": now,
    }


def downgrade() -> None:
    bind = op.get_bind()
    reservations = sa.table("ai_usage_reservations", sa.column("policy_id", sa.Uuid()))
    counters = sa.table("ai_usage_counters", sa.column("policy_id", sa.Uuid()))
    for table in (reservations, counters):
        if bind.scalar(
            sa.select(sa.func.count()).select_from(table).where(table.c.policy_id.in_(_SEEDED_IDS))
        ):
            raise RuntimeError("Refusing downgrade: seeded AI allowance records remain.")
    policies = sa.table("ai_usage_policies", sa.column("id", sa.Uuid()))
    bind.execute(sa.delete(policies).where(policies.c.id.in_(_SEEDED_IDS)))
