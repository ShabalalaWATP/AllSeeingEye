"""Retire the legacy global Manager account role.

Revision ID: 0050
Revises: 0049

Before this revision a non-administrator needed BOTH the global Manager account
role AND a team Manager membership to lead a team. Afterwards the membership
alone is the authority. A team Manager membership held by an ordinary ``user``
account previously granted nothing, so it is demoted to Member first; otherwise
it would silently gain authority. Only then are global Manager accounts
converted to ordinary users, keeping their memberships. Security versions are
bumped so sessions issued under the old role cannot be reused.

Demotions and any active team left without an active Manager are inventoried
per team (identifiers and counts only, never emails) in the administrator audit
log and the migration log, for explicit administrator review.
"""

import logging
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")

users = sa.table(
    "users",
    sa.column("id", sa.Uuid()),
    sa.column("role", sa.String(16)),
    sa.column("is_active", sa.Boolean()),
    sa.column("security_version", sa.Integer()),
)
teams = sa.table("teams", sa.column("id", sa.Uuid()), sa.column("is_active", sa.Boolean()))
memberships = sa.table(
    "team_memberships",
    sa.column("team_id", sa.Uuid()),
    sa.column("user_id", sa.Uuid()),
    sa.column("role", sa.String(16)),
)
audit = sa.table(
    "audit_log",
    sa.column("at", sa.DateTime(timezone=True)),
    sa.column("actor_user_id", sa.Uuid()),
    sa.column("action", sa.String(64)),
    sa.column("subject", sa.String(320)),
    sa.column("ip", sa.String(64)),
    sa.column("details", sa.JSON()),
)


def _record(connection: sa.Connection, team_id: object, details: dict[str, object]) -> None:
    connection.execute(
        audit.insert().values(
            at=datetime.now(UTC),
            actor_user_id=None,
            action="team_authority_migrated",
            subject=f"team:{team_id}",
            ip=None,
            details={"revision": revision, "team_id": str(team_id), **details},
        )
    )


def upgrade() -> None:
    connection = op.get_bind()
    ordinary_managers = sa.and_(
        memberships.c.role == "manager",
        memberships.c.user_id.in_(sa.select(users.c.id).where(users.c.role == "user")),
    )
    demoted = list(
        connection.execute(
            sa.select(memberships.c.team_id, sa.func.count())
            .where(ordinary_managers)
            .group_by(memberships.c.team_id)
        )
    )
    connection.execute(sa.update(memberships).where(ordinary_managers).values(role="member"))
    for team_id, count in demoted:
        _record(
            connection,
            team_id,
            {"reason": "ordinary_account_manager_demoted", "demoted_memberships": int(count)},
        )
    connection.execute(
        sa.update(users)
        .where(users.c.role == "manager")
        .values(role="user", security_version=users.c.security_version + 1)
    )
    active_manager = (
        sa.select(memberships.c.user_id)
        .join(users, users.c.id == memberships.c.user_id)
        .where(
            memberships.c.team_id == teams.c.id,
            memberships.c.role == "manager",
            users.c.is_active.is_(True),
        )
        .exists()
    )
    unmanaged = [
        row.id
        for row in connection.execute(
            sa.select(teams.c.id).where(teams.c.is_active.is_(True), ~active_manager)
        )
    ]
    for team_id in unmanaged:
        _record(connection, team_id, {"reason": "active_team_without_active_manager"})
    log.warning(
        "0050 demoted ordinary-account Manager memberships in %d team(s); "
        "%d active team(s) have no active Manager: %s",
        len(demoted),
        len(unmanaged),
        ", ".join(str(team_id) for team_id in unmanaged) or "none",
    )


def downgrade() -> None:
    # The conversion is intentionally one-way.  Restoring a global role or a
    # demoted membership would silently grant authority that now belongs to
    # explicit team membership and administrator review.
    pass
