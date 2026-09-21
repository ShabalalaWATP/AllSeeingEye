"""Authorised tier administration and atomic admission of one research run."""

from datetime import datetime
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.policy import require_admin
from ase.application.ports import Clock, UnitOfWork, UserRepository
from ase.application.ports.research_usage import ResearchUsageRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.research_usage import (
    ResearchAllowance,
    ResearchUsageLimit,
    period_bounds,
    tier_policy,
)
from ase.domain.users import User


class ResearchUsageService:
    def __init__(
        self,
        repository: ResearchUsageRepository,
        users: UserRepository,
        access: AccessPolicy,
        clock: Clock,
        uow: UnitOfWork,
        auditor: Auditor,
    ) -> None:
        self._repo, self._users, self._access = repository, users, access
        self._clock, self._uow, self._auditor = clock, uow, auditor

    async def allowance(self, user_id: UUID, now: datetime) -> ResearchAllowance:
        tier, revision = await self._repo.assignment(user_id)
        policy = tier_policy(tier)
        start, end = period_bounds(now, policy.period)
        used = await self._repo.used(user_id, policy.period, start)
        return ResearchAllowance(
            policy.tier,
            policy.label,
            policy.limit,
            policy.period,
            used,
            None if policy.limit is None else max(0, policy.limit - used),
            start,
            end,
            revision,
        )

    async def me(self, actor: User) -> ResearchAllowance:
        current = await self._access.context(actor)
        return await self.allowance(current.actor.id, self._clock.now())

    async def list_users(self, actor: User) -> list[tuple[UUID, ResearchAllowance]]:
        current = await self._access.context(actor)
        require_admin(current.actor)
        now = self._clock.now()
        return [
            (user.id, await self.allowance(user.id, now)) for user in await self._users.list_all()
        ]

    async def assign(
        self, actor: User, user_id: UUID, tier: int, expected_revision: int, context: RequestContext
    ) -> ResearchAllowance:
        """Changing the tier never resets daily or weekly usage or modifies account privileges."""
        tier_policy(tier)
        if type(expected_revision) is not int or expected_revision < 0:
            raise InvalidRequest("Research level revisions must be non-negative whole numbers.")
        try:
            current = await self._access.context(actor, for_update=True)
            require_admin(current.actor)
            if await self._users.lock_by_id(user_id) is None:
                raise NotFound()
            previous_tier, revision = await self._repo.assignment(user_id)
            if revision != expected_revision:
                raise Conflict("This research level changed. Reload it before saving again.")
            await self._repo.assign(user_id, tier, revision + 1)
            await self._auditor.record(
                AuditAction.RESEARCH_TIER_ASSIGNED,
                actor=current.actor.id,
                subject=str(user_id),
                ip=context.ip,
                details={"previous_tier": previous_tier, "tier": tier, "revision": revision + 1},
            )
            result = await self.allowance(user_id, self._clock.now())
            await self._uow.commit()
            return result
        except BaseException:
            await self._uow.rollback()
            raise

    async def admit_locked(self, user_id: UUID, now: datetime) -> None:
        """Charge once in the job transaction, after the caller locks and validates its owner.

        Both counters advance so a subsequent tier change cannot erase admitted work.
        There are no refunds: failure, cancellation and deletion still consumed a run.
        """
        allowance = await self.allowance(user_id, now)
        if allowance.remaining == 0:
            raise ResearchUsageLimit(allowance, now)
        for period in ("day", "week"):
            start, _ = period_bounds(now, period)
            await self._repo.increment(user_id, period, start)

    async def admit(self, actor: User, team_id: UUID | None, *, automation: bool = False) -> None:
        """Commit synchronous admission before any paid work, releasing all database locks."""
        try:
            access = (
                await self._access.background(actor.id, team_id, for_update=True)
                if automation
                else await self._access.context(actor, for_update=True)
            )
            access.require_create(team_id)
            await self.admit_locked(access.actor.id, self._clock.now())
            await self._uow.commit()
        except BaseException:
            await self._uow.rollback()
            raise
