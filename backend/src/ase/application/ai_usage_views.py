"""Authorised read models for AI allowances and observed usage.

Members see only their own attributed team usage, team Managers see team aggregates
and member totals, and administrators see any team, account or system budget.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from ase.application.policy import require_admin
from ase.application.ports.ai_usage import AiUsageRepository
from ase.application.ports.repositories import UserRepository
from ase.application.ports.teams import TeamRepository
from ase.domain.ai_usage import (
    AiMemberUsage,
    AiReservationStatus,
    AiUsageSummary,
    AiUsageTotals,
)
from ase.domain.errors import NotFound, Unauthenticated
from ase.domain.teams import MembershipRole
from ase.domain.users import User

if TYPE_CHECKING:
    from ase.application.ports import Clock

TeamUsageView = Literal["member", "manager", "admin"]


@dataclass(frozen=True, slots=True)
class AccountAiUsage:
    summaries: list[AiUsageSummary]
    totals: AiUsageTotals


@dataclass(frozen=True, slots=True)
class TeamAiUsage:
    team_id: UUID
    view: TeamUsageView
    summaries: list[AiUsageSummary]
    own: AiUsageTotals
    team: AiUsageTotals | None
    members: list[AiMemberUsage] | None


@dataclass(frozen=True, slots=True)
class AiUsagePreview:
    summaries: list[AiUsageSummary]
    totals: AiUsageTotals
    unknown_calls: int


class AiUsageViews:
    def __init__(
        self,
        repository: AiUsageRepository,
        teams: TeamRepository,
        users: UserRepository,
        clock: Clock,
    ) -> None:
        self._repository, self._teams = repository, teams
        self._users, self._clock = users, clock

    async def _fresh(self, actor: User) -> User:
        fresh = await self._users.get_by_id(actor.id)
        if fresh is None or not fresh.is_active or fresh.security_version != actor.security_version:
            raise Unauthenticated()
        return fresh

    async def mine(self, actor: User) -> AccountAiUsage:
        actor = await self._fresh(actor)
        now = self._clock.now()
        policies = await self._repository.view_policies(user_id=actor.id, team_id=None)
        return AccountAiUsage(
            await self._repository.summaries_for(policies, now),
            await self._repository.account_totals(actor.id, now),
        )

    async def team(self, actor: User, team_id: UUID) -> TeamAiUsage:
        actor = await self._fresh(actor)
        team = await self._teams.get(team_id)
        membership = await self._teams.get_membership(team_id, actor.id)
        if team is None or (membership is None and not actor.is_admin):
            raise NotFound()  # Never disclose another team's existence or policy.
        view: TeamUsageView = (
            "admin"
            if actor.is_admin
            else "manager"
            if membership is not None and membership.role is MembershipRole.MANAGER
            else "member"
        )
        now = self._clock.now()
        policies = await self._repository.view_policies(user_id=None, team_id=team_id)
        own = await self._repository.team_totals(team_id, now, user_id=actor.id)
        if view == "member":
            return TeamAiUsage(
                team_id, view, await self._repository.summaries_for(policies, now), own, None, None
            )
        return TeamAiUsage(
            team_id,
            view,
            await self._repository.summaries_for(policies, now),
            own,
            await self._repository.team_totals(team_id, now),
            await self._repository.team_member_totals(team_id, now),
        )

    async def preview(
        self,
        actor: User,
        *,
        user_id: UUID | None,
        team_id: UUID | None,
        system: bool = False,
    ) -> AiUsagePreview:
        """Show the policies a call would be charged to, without requiring membership."""
        require_admin(await self._fresh(actor))
        now = self._clock.now()
        unknown = await self._repository.count_reservations(AiReservationStatus.UNKNOWN)
        if system:
            policies = await self._repository.view_policies(user_id=None, team_id=None, system=True)
            return AiUsagePreview(
                await self._repository.summaries_for(policies, now),
                await self._repository.system_totals(now),
                unknown,
            )
        if user_id is None or await self._users.get_by_id(user_id) is None:
            raise NotFound()
        if team_id is not None and (
            await self._teams.get(team_id) is None
            or not await self._repository.can_attribute_to_team(user_id, team_id)
        ):
            raise NotFound()
        policies = await self._repository.view_policies(user_id=user_id, team_id=team_id)
        totals = (
            await self._repository.team_totals(team_id, now, user_id=user_id)
            if team_id is not None
            else await self._repository.account_totals(user_id, now)
        )
        return AiUsagePreview(await self._repository.summaries_for(policies, now), totals, unknown)
