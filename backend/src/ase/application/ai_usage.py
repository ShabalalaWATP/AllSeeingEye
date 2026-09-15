"""Admission accounting for AI usage: reserve, dispatch, finish and reconcile.

Each step opens its own short transaction; none is held across a provider request.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID, uuid4

from ase.application.ports.ai_usage import AiUsageRepository
from ase.domain.ai_usage import (
    STALE_RESERVATION_AGE,
    AiAttribution,
    AiCallOutcome,
    AiUsageReservation,
)

if TYPE_CHECKING:
    from ase.application.ports import Clock

log = logging.getLogger(__name__)
SETTLEMENT_SECONDS = 3.0
RECONCILE_INTERVAL_SECONDS = 60.0
RECONCILE_BATCH = 20


class AiUsageTransaction(Protocol):
    """The short-lived transaction each accounting step opens and closes."""

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


@dataclass(frozen=True, slots=True)
class AiReservationBatch:
    """Every policy reservation for one provider call, plus its observed attribution."""

    call_id: UUID
    attribution: AiAttribution
    reserved_at: datetime
    requested_tokens: int
    reservations: tuple[AiUsageReservation, ...]


@dataclass(frozen=True, slots=True)
class AiReconciliation:
    released: int = 0
    unknown: int = 0


class AiUsageAccounting:
    """Open short database transactions around a model call, never across the network."""

    def __init__(
        self,
        session_factory: Callable[[], AbstractAsyncContextManager[AiUsageTransaction]],
        repository_factory: Callable[[Any], AiUsageRepository],
        clock: Clock,
        *,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._session_factory = session_factory
        self._repository_factory = repository_factory
        self._clock = clock
        self._monotonic = monotonic
        self._next_reconcile = 0.0

    async def reserve(
        self,
        attribution: AiAttribution,
        *,
        profile_id: UUID | None,
        model: str,
        purpose: str,
        requested_tokens: int,
    ) -> AiReservationBatch:
        """Admit one call under every applicable policy, or record it for observation only."""
        await self._maybe_reconcile()
        now = self._clock.now()
        call_id = uuid4()
        async with self._session_factory() as session:
            repository = self._repository_factory(session)
            try:
                if (
                    attribution.team_id is not None
                    and attribution.user_id is not None
                    and not await repository.can_attribute_to_team(
                        attribution.user_id, attribution.team_id
                    )
                ):
                    # A caller cannot charge, or read, a team it cannot act for.
                    attribution = AiAttribution.actor(attribution.user_id)
                policies = await repository.effective_policies(attribution)
                reservations = [
                    await repository.reserve(
                        policy.id,
                        call_id=call_id,
                        attribution=attribution,
                        profile_id=profile_id,
                        model=model,
                        purpose=purpose,
                        requested_tokens=requested_tokens,
                        now=now,
                    )
                    for policy in sorted(policies, key=lambda item: item.id)
                ]
                await session.commit()
            except BaseException:
                await session.rollback()
                raise
        return AiReservationBatch(call_id, attribution, now, requested_tokens, tuple(reservations))

    async def mark_dispatched(self, batch: AiReservationBatch) -> None:
        if not batch.reservations:
            return
        async with self._session_factory() as session:
            try:
                await self._repository_factory(session).mark_dispatched(
                    batch.call_id, self._clock.now()
                )
                await session.commit()
            except BaseException:
                await session.rollback()
                raise

    async def finish(
        self,
        batch: AiReservationBatch,
        outcome: AiCallOutcome,
        *,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        error: str | None = None,
    ) -> None:
        async with self._session_factory() as session:
            try:
                await self._repository_factory(session).finish(
                    batch.call_id,
                    outcome=outcome,
                    attribution=batch.attribution,
                    reserved_at=batch.reserved_at,
                    requested_tokens=batch.requested_tokens,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    error=error,
                    now=self._clock.now(),
                )
                await session.commit()
            except BaseException:
                await session.rollback()
                raise

    async def reconcile(self, limit: int = RECONCILE_BATCH) -> AiReconciliation:
        """Release stale undispatched reservations; hold dispatched ones as unknown."""
        now = self._clock.now()
        released = unknown = 0
        async with self._session_factory() as session:
            repository = self._repository_factory(session)
            try:
                for stale in await repository.stale_reservations(
                    now - STALE_RESERVATION_AGE, limit
                ):
                    outcome = (
                        AiCallOutcome.NOT_DISPATCHED
                        if stale.dispatched_at is None
                        else AiCallOutcome.UNKNOWN
                    )
                    await repository.finish(
                        stale.call_id,
                        outcome=outcome,
                        attribution=stale.attribution,
                        reserved_at=stale.created_at,
                        requested_tokens=stale.reserved_tokens,
                        prompt_tokens=None,
                        completion_tokens=None,
                        error="reconciled_stale_reservation",
                        now=now,
                    )
                    if outcome is AiCallOutcome.UNKNOWN:
                        unknown += 1
                    else:
                        released += 1
                await session.commit()
            except BaseException:
                await session.rollback()
                raise
        return AiReconciliation(released, unknown)

    async def _maybe_reconcile(self) -> None:
        """Opportunistic, throttled and bounded; a failure never blocks admission."""
        current = self._monotonic()
        if current < self._next_reconcile:
            return
        self._next_reconcile = current + RECONCILE_INTERVAL_SECONDS
        try:
            async with asyncio.timeout(SETTLEMENT_SECONDS):
                await self.reconcile()
        except Exception:
            log.warning("ai_usage.reconcile_failed", exc_info=True)


async def finish_with_deadline(
    accounting: AiUsageAccounting,
    batch: AiReservationBatch,
    outcome: AiCallOutcome,
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    error: str | None = None,
) -> bool:
    """Keep provider cleanup bounded; never retry an uncertain settlement.

    An unconfirmed write leaves the reservation ``reserved``; reconciliation later
    releases it or holds it as unknown, depending on whether dispatch was recorded.
    """
    try:
        async with asyncio.timeout(SETTLEMENT_SECONDS):
            await accounting.finish(
                batch,
                outcome,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                error=error,
            )
    except (Exception, asyncio.CancelledError):
        return False
    return True
