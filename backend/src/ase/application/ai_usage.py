"""Admission and administration services for AI usage policies."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID, uuid4

from ase.application.policy import require_admin
from ase.application.ports.ai_usage import AiUsageRepository
from ase.domain.ai_usage import (
    AiAllowancePeriod,
    AiPolicyScope,
    AiUsagePolicy,
    AiUsageReservation,
    AiUsageSummary,
)
from ase.domain.errors import Conflict, NotFound
from ase.domain.users import User

if TYPE_CHECKING:
    from ase.application.ports import Clock


class AiUsageTransaction(Protocol):
    """The short-lived transaction each accounting step opens and closes."""

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...



@dataclass(frozen=True, slots=True)
class AiReservationBatch:
    """All policy reservations for one provider request."""

    reservations: tuple[AiUsageReservation, ...]


class AiUsageAccounting:
    """Open short database transactions around a model call, never across the network."""

    def __init__(
        self,
        session_factory: Callable[[], AbstractAsyncContextManager[AiUsageTransaction]],
        repository_factory: Callable[[Any], AiUsageRepository],
        clock: Clock,
    ) -> None:
        self._session_factory = session_factory
        self._repository_factory = repository_factory
        self._clock = clock

    async def reserve(
        self,
        user_id: UUID,
        *,
        team_id: UUID | None = None,
        profile_id: UUID | None,
        model: str,
        purpose: str,
        requested_tokens: int,
    ) -> AiReservationBatch | None:
        async with self._session_factory() as session:
            repository = self._repository_factory(session)
            policies = await repository.effective_policies(user_id, team_id=team_id)
            if not policies:
                # Existing installations without an administrator policy retain their
                # historical behaviour. Adding a global policy enables enforcement.
                return None
            reservations: list[AiUsageReservation] = []
            try:
                for policy in policies:
                    reservations.append(
                        await repository.reserve(
                            policy.id,
                            user_id=user_id,
                            profile_id=profile_id,
                            model=model,
                            purpose=purpose,
                            requested_tokens=requested_tokens,
                            now=self._clock.now(),
                        )
                    )
                await session.commit()
            except BaseException:
                await session.rollback()
                raise
            return AiReservationBatch(tuple(reservations))

    async def settle(
        self,
        batch: AiReservationBatch | None,
        *,
        ok: bool,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        error: str | None,
    ) -> None:
        if batch is None:
            return
        async with self._session_factory() as session:
            repository = self._repository_factory(session)
            try:
                for reservation in batch.reservations:
                    await repository.settle(
                        reservation.id,
                        ok=ok,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        error=error,
                        now=self._clock.now(),
                    )
                await session.commit()
            except BaseException:
                await session.rollback()
                raise

    async def summaries(
        self, user_id: UUID, *, team_id: UUID | None = None
    ) -> list[AiUsageSummary]:
        async with self._session_factory() as session:
            repository = self._repository_factory(session)
            return await repository.summary(user_id, now=self._clock.now(), team_id=team_id)


@dataclass(frozen=True, slots=True)
class AiPolicyInput:
    scope: AiPolicyScope
    target_id: UUID | None
    period: AiAllowancePeriod
    request_limit: int | None
    token_limit: int | None
    enabled: bool


def _policy_from_input(data: AiPolicyInput, *, now: datetime, policy_id: UUID) -> AiUsagePolicy:
    return AiUsagePolicy(
        policy_id,
        data.scope,
        data.target_id,
        data.period,
        data.request_limit,
        data.token_limit,
        data.enabled,
        1,
        now,
        now,
    )


class AiUsagePolicyAdmin:
    """Admin-only CRUD; policy edits become effective on the next admission decision."""

    def __init__(self, repository: AiUsageRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def list(self, actor: User) -> list[AiUsagePolicy]:
        require_admin(actor)
        return await self._repository.list_policies()

    async def create(self, actor: User, data: AiPolicyInput) -> AiUsagePolicy:
        require_admin(actor)
        existing = await self._repository.find_policy(data.scope, data.target_id)
        if existing is not None:
            raise Conflict("An AI policy already exists for this target.")
        policy = _policy_from_input(data, now=self._clock.now(), policy_id=uuid4())
        await self._repository.add_policy(policy)
        return policy

    async def update(self, actor: User, policy_id: UUID, data: AiPolicyInput) -> AiUsagePolicy:
        require_admin(actor)
        current = await self._repository.get_policy(policy_id)
        if current is None:
            raise NotFound()
        existing = await self._repository.find_policy(data.scope, data.target_id)
        if existing is not None and existing.id != current.id:
            raise Conflict("An AI policy already exists for this target.")
        updated = AiUsagePolicy(
            current.id,
            data.scope,
            data.target_id,
            data.period,
            data.request_limit,
            data.token_limit,
            data.enabled,
            current.revision + 1,
            current.created_at,
            self._clock.now(),
        )
        await self._repository.save_policy(updated)
        return updated

    async def disable(self, actor: User, policy_id: UUID) -> None:
        require_admin(actor)
        current = await self._repository.get_policy(policy_id)
        if current is None:
            raise NotFound()
        await self.update(
            actor,
            policy_id,
            AiPolicyInput(
                current.scope,
                current.target_id,
                current.period,
                current.request_limit,
                current.token_limit,
                False,
            ),
        )


async def settle_with_deadline(
    accounting: AiUsageAccounting,
    batch: AiReservationBatch | None,
    *,
    ok: bool,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    error: str | None,
) -> bool:
    """Keep provider cleanup bounded; never retry an uncertain settlement."""
    if batch is None:
        return True
    try:
        async with asyncio.timeout(3):
            await accounting.settle(
                batch,
                ok=ok,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                error=error,
            )
    except (Exception, asyncio.CancelledError):
        return False
    return True
