"""Backfill creator memberships and index team leadership checks.

Revision ID: 0047
Revises: 0046

Every creator membership this revision adds or promotes is inventoried per team
in the administrator audit log and the migration log, so the authority granted
without an interactive actor remains reviewable.
"""

import logging
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

log = logging.getLogger("alembic.runtime.migration")

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("teams", sa.Column("description", sa.String(500), nullable=True))
    op.create_index(
        "ix_team_memberships_team_role",
        "team_memberships",
        ["team_id", "role"],
    )

    teams = sa.table(
        "teams",
        sa.column("id", sa.Uuid()),
        sa.column("created_by", sa.Uuid()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("is_active", sa.Boolean()),
    )
    memberships = sa.table(
        "team_memberships",
        sa.column("team_id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("role", sa.String(16)),
        sa.column("joined_at", sa.DateTime(timezone=True)),
    )
    already_member = sa.exists().where(
        memberships.c.team_id == teams.c.id,
        memberships.c.user_id == teams.c.created_by,
    )
    active_creator_membership = sa.exists().where(
        teams.c.id == memberships.c.team_id,
        teams.c.created_by == memberships.c.user_id,
        users.c.id == teams.c.created_by,
        users.c.is_active.is_(True),
    )
    connection = op.get_bind()
    promoted = [
        row.id
        for row in connection.execute(
            sa.select(teams.c.id)
            .select_from(
                teams.join(users, users.c.id == teams.c.created_by).join(
                    memberships,
                    sa.and_(
                        memberships.c.team_id == teams.c.id,
                        memberships.c.user_id == teams.c.created_by,
                    ),
                )
            )
            .where(users.c.is_active.is_(True), memberships.c.role != "manager")
        )
    ]
    inserted = [
        row.id
        for row in connection.execute(
            sa.select(teams.c.id)
            .select_from(teams.join(users, users.c.id == teams.c.created_by))
            .where(users.c.is_active.is_(True), ~already_member)
        )
    ]
    op.execute(sa.update(memberships).where(active_creator_membership).values(role="manager"))
    op.execute(
        sa.insert(memberships).from_select(
            [
                memberships.c.team_id,
                memberships.c.user_id,
                memberships.c.role,
                memberships.c.joined_at,
            ],
            sa.select(
                teams.c.id,
                teams.c.created_by,
                sa.literal("manager", type_=sa.String(16)),
                teams.c.created_at,
            )
            .select_from(teams.join(users, users.c.id == teams.c.created_by))
            .where(users.c.is_active.is_(True), ~already_member),
        )
    )
    _record_inventory(connection, promoted, "creator_membership_promoted")
    _record_inventory(connection, inserted, "creator_membership_added")


def _record_inventory(connection: sa.Connection, team_ids: list[object], reason: str) -> None:
    """Audit each team whose creator gained Manager authority, without personal data."""
    if not team_ids:
        return
    audit = sa.table(
        "audit_log",
        sa.column("at", sa.DateTime(timezone=True)),
        sa.column("actor_user_id", sa.Uuid()),
        sa.column("action", sa.String(64)),
        sa.column("subject", sa.String(320)),
        sa.column("ip", sa.String(64)),
        sa.column("details", sa.JSON()),
    )
    now = datetime.now(UTC)
    for team_id in team_ids:
        connection.execute(
            audit.insert().values(
                at=now,
                actor_user_id=None,
                action="team_authority_migrated",
                subject=f"team:{team_id}",
                ip=None,
                details={"revision": revision, "team_id": str(team_id), "reason": reason},
            )
        )
    log.warning("0047 %s: %d team(s) inventoried in the audit log", reason, len(team_ids))


def downgrade() -> None:
    # The backfilled memberships are valid domain data. Removing them during a
    # downgrade could silently orphan teams, so retain the data and remove only
    # the supporting index.
    op.drop_index("ix_team_memberships_team_role", table_name="team_memberships")
    op.drop_column("teams", "description")
