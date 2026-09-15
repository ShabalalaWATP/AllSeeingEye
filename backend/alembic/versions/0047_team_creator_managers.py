"""Backfill creator memberships and index team leadership checks.

Revision ID: 0047
Revises: 0046
"""

import sqlalchemy as sa
from alembic import op

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


def downgrade() -> None:
    # The backfilled memberships are valid domain data. Removing them during a
    # downgrade could silently orphan teams, so retain the data and remove only
    # the supporting index.
    op.drop_index("ix_team_memberships_team_role", table_name="team_memberships")
    op.drop_column("teams", "description")
