"""Shared fixtures for AI allowance accounting tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ase.application.ai_usage import AiReservationBatch, AiUsageAccounting
from ase.domain.ai_usage import (
    AiAllowancePeriod,
    AiAttribution,
    AiCallOutcome,
    AiPolicyScope,
    AiUsagePolicy,
)

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)


def policy(
    *,
    limit: int | None = 2,
    tokens: int | None = 100,
    scope: AiPolicyScope = AiPolicyScope.GLOBAL,
    target_id: UUID | None = None,
    period: AiAllowancePeriod = AiAllowancePeriod.MONTH,
) -> AiUsagePolicy:
    return AiUsagePolicy(uuid4(), scope, target_id, period, limit, tokens, True, 1, NOW, NOW)


async def add_policy(container, current: AiUsagePolicy) -> None:
    async with container.session_factory() as session:
        await container.repositories(session).ai_usage.add_policy(current)
        await session.commit()


def accounting(container) -> AiUsageAccounting:
    return AiUsageAccounting(
        container.session_factory,
        lambda session: container.repositories(session).ai_usage,
        container.clock,
    )


async def summaries(container, user_id: UUID, team_id: UUID | None = None):
    async with container.session_factory() as session:
        repo = container.repositories(session).ai_usage
        policies = await repo.view_policies(user_id=user_id, team_id=team_id)
        return await repo.summaries_for(policies, container.clock.now())


async def reservations(container):
    async with container.session_factory() as session:
        return await container.repositories(session).ai_usage.list_reservations()


class FakeAccounting:
    """Records the accounting protocol without a database."""

    def __init__(self, *, reserve_error: BaseException | None = None) -> None:
        self.reserved: list[tuple[AiAttribution, dict]] = []
        self.dispatched: list[AiReservationBatch] = []
        self.finished: list[tuple[AiCallOutcome, dict]] = []
        self.reserve_error = reserve_error
        self.dispatch_error: BaseException | None = None
        self.finish_error: BaseException | None = None

    async def reserve(self, attribution: AiAttribution, **kwargs) -> AiReservationBatch:
        self.reserved.append((attribution, kwargs))
        if self.reserve_error is not None:
            raise self.reserve_error
        return AiReservationBatch(uuid4(), attribution, NOW, kwargs["requested_tokens"], ())

    async def mark_dispatched(self, batch: AiReservationBatch) -> None:
        if self.dispatch_error is not None:
            raise self.dispatch_error
        self.dispatched.append(batch)

    async def finish(self, batch: AiReservationBatch, outcome: AiCallOutcome, **kwargs) -> None:
        if self.finish_error is not None:
            raise self.finish_error
        self.finished.append((outcome, kwargs))


class Blocking:
    """A provider that waits until cancelled or released."""

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def complete(self, *_args):
        self.started.set()
        await self.release.wait()
        raise AssertionError("released unexpectedly")
