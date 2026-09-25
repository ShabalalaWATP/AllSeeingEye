"""Team rows and repositories; no-op updates provide SQLite and PostgreSQL locking."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Uuid,
    delete,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.adapters.persistence.directory_profile import DirectoryProfileRow
from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.session_changes import mark_session_change
from ase.domain.errors import NotFound
from ase.domain.teams import MembershipRole, Team, TeamMember, TeamMembership
from ase.domain.users import Role


class TeamRow(Base):
    __tablename__ = "teams"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class TeamMembershipRow(Base):
    __tablename__ = "team_memberships"
    __table_args__ = (
        CheckConstraint("role IN ('member', 'manager')", name="ck_membership_role"),
        Index("ix_team_memberships_team_role", "team_id", "role"),
    )

    team_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("teams.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    joined_at: Mapped[datetime] = mapped_column(UTCDateTime)


def _team(row: TeamRow) -> Team:
    return Team(
        row.id,
        row.name,
        row.is_active,
        row.created_by,
        row.created_at,
        row.updated_at,
        row.description,
    )


class SqlTeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, team: Team) -> None:
        self._session.add(
            TeamRow(
                id=team.id,
                name=team.name,
                is_active=team.is_active,
                created_by=team.created_by,
                created_at=team.created_at,
                updated_at=team.updated_at,
                description=team.description,
            )
        )
        await self._session.flush()

    async def get(self, team_id: UUID) -> Team | None:
        row = await self._session.scalar(
            select(TeamRow).where(TeamRow.id == team_id).execution_options(populate_existing=True)
        )
        return _team(row) if row else None

    async def get_for_update(self, team_id: UUID) -> Team | None:
        # FOR UPDATE is ignored by SQLite. An UPDATE takes its writer lock and a PG row lock.
        await self._session.execute(
            update(TeamRow).where(TeamRow.id == team_id).values(updated_at=TeamRow.updated_at)
        )
        return await self.get(team_id)

    async def save(self, team: Team) -> None:
        row = await self._session.get(TeamRow, team.id)
        if row is None:
            raise NotFound()
        if row.is_active != team.is_active:
            members = await self._session.scalars(
                select(TeamMembershipRow.user_id).where(TeamMembershipRow.team_id == team.id)
            )
            for member in members:
                mark_session_change(self._session, member)
        row.name, row.is_active, row.updated_at, row.description = (
            team.name,
            team.is_active,
            team.updated_at,
            team.description,
        )
        await self._session.flush()

    async def list_visible(self, user_id: UUID, *, administrator: bool) -> list[Team]:
        statement = select(TeamRow)
        if not administrator:
            statement = statement.join(TeamMembershipRow).where(
                TeamMembershipRow.user_id == user_id
            )
        rows = await self._session.scalars(statement.order_by(TeamRow.name, TeamRow.id))
        return [_team(row) for row in rows]

    async def count_active_created_by(self, user_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count())
                .select_from(TeamRow)
                .where(
                    TeamRow.created_by == user_id,
                    TeamRow.is_active.is_(True),
                )
            )
            or 0
        )

    async def get_membership(self, team_id: UUID, user_id: UUID) -> TeamMembership | None:
        row = await self._session.scalar(
            select(TeamMembershipRow)
            .where(
                TeamMembershipRow.team_id == team_id,
                TeamMembershipRow.user_id == user_id,
            )
            .execution_options(populate_existing=True)
        )
        return (
            TeamMembership(row.team_id, row.user_id, MembershipRole(row.role), row.joined_at)
            if row
            else None
        )

    async def list_members(self, team_id: UUID) -> list[TeamMember]:
        rows = await self._session.execute(
            select(TeamMembershipRow, UserRow, DirectoryProfileRow.username)
            .select_from(TeamMembershipRow)
            .join(UserRow, UserRow.id == TeamMembershipRow.user_id)
            .outerjoin(DirectoryProfileRow, DirectoryProfileRow.user_id == UserRow.id)
            .where(
                TeamMembershipRow.team_id == team_id,
            )
            .order_by(UserRow.display_name, UserRow.id)
            .execution_options(populate_existing=True)
        )
        return [
            TeamMember(
                user.id,
                user.display_name,
                Role(user.role),
                user.is_active,
                MembershipRole(member.role),
                member.joined_at,
                username,
            )
            for member, user, username in rows
        ]

    async def count_members(self, team_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count())
                .select_from(TeamMembershipRow)
                .where(TeamMembershipRow.team_id == team_id)
            )
            or 0
        )

    async def memberships_for_user(self, user_id: UUID) -> list[TeamMembership]:
        rows = await self._session.scalars(
            select(TeamMembershipRow)
            .where(TeamMembershipRow.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        return [
            TeamMembership(row.team_id, row.user_id, MembershipRole(row.role), row.joined_at)
            for row in rows
        ]

    async def count_active_managers(self, team_id: UUID) -> int:
        """Return managers whose account is still active.

        Team mutations hold the team's row lock before calling this method. The
        join deliberately counts current account state, so an inactive account
        cannot keep an active team looking managed.
        """
        statement = (
            select(func.count())
            .select_from(TeamMembershipRow)
            .join(UserRow, UserRow.id == TeamMembershipRow.user_id)
            .where(
                TeamMembershipRow.team_id == team_id,
                TeamMembershipRow.role == MembershipRole.MANAGER.value,
                UserRow.is_active.is_(True),
            )
        )
        return int(await self._session.scalar(statement) or 0)

    async def count_teams_only_managed_by(self, user_id: UUID) -> int:
        """Count active teams where this active account is the sole active Manager."""
        other = TeamMembershipRow.__table__.alias("other_manager")
        other_user = UserRow.__table__.alias("other_user")
        another_active_manager = (
            select(other.c.user_id)
            .join(other_user, other_user.c.id == other.c.user_id)
            .where(
                other.c.team_id == TeamMembershipRow.team_id,
                other.c.user_id != user_id,
                other.c.role == MembershipRole.MANAGER.value,
                other_user.c.is_active.is_(True),
            )
            .exists()
        )
        statement = (
            select(func.count())
            .select_from(TeamMembershipRow)
            .join(TeamRow, TeamRow.id == TeamMembershipRow.team_id)
            .join(UserRow, UserRow.id == TeamMembershipRow.user_id)
            .where(
                TeamMembershipRow.user_id == user_id,
                TeamMembershipRow.role == MembershipRole.MANAGER.value,
                TeamRow.is_active.is_(True),
                UserRow.is_active.is_(True),
                ~another_active_manager,
            )
        )
        return int(await self._session.scalar(statement) or 0)

    async def put_membership(self, membership: TeamMembership) -> None:
        # Callers hold the team mutation lock, so duplicate requests cannot race the insert.
        row = await self._session.get(TeamMembershipRow, (membership.team_id, membership.user_id))
        mark_session_change(self._session, membership.user_id)
        if row is None:
            self._session.add(
                TeamMembershipRow(
                    team_id=membership.team_id,
                    user_id=membership.user_id,
                    role=membership.role.value,
                    joined_at=membership.joined_at,
                )
            )
        else:
            row.role = membership.role.value
        await self._session.flush()

    async def remove_membership(self, team_id: UUID, user_id: UUID) -> None:
        mark_session_change(self._session, user_id)
        await self._session.execute(
            delete(TeamMembershipRow).where(
                TeamMembershipRow.team_id == team_id,
                TeamMembershipRow.user_id == user_id,
            )
        )
        await self._session.flush()
