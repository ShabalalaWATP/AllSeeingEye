"""Execute one evaluation run in the background, outside any request transaction.

Every provider call first consumes one call of the run's durable cap, which also
observes a cancellation from any process, and then passes through the AI allowance
ledger. Failed calls keep their slot. After each case's model work the owner and
connection are checked again before the summary is saved. Each database step is its
own short transaction; none is held across a model call, and the administration
guard is only taken inside them.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Coroutine
from contextlib import suppress
from typing import Any
from uuid import UUID

from ase.application.ai_usage import AiUsageAccounting
from ase.application.ai_usage_gateway import AllowanceLlmGateway
from ase.application.policy import require_admin
from ase.application.ports import Clock
from ase.application.ports.evaluations import (
    CallReservation,
    EvaluationHarness,
    EvaluationSession,
    EvaluationUnit,
    EvaluationUnitFactory,
)
from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.domain.ai_usage import AiAllowanceExceeded, AiAttribution
from ase.domain.errors import Forbidden, Unauthenticated
from ase.domain.evaluations import (
    RUN_LEASE,
    EvaluationConnection,
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationStopReason,
)
from ase.domain.llm import LlmProfile, LlmRequest, LlmResult

log = logging.getLogger(__name__)
Outcome = tuple[EvaluationRunStatus, EvaluationStopReason | None]
STOPPED = EvaluationRunStatus.STOPPED
# Without an owner or with a changed connection, no further output is retained.
UNRETAINED = {EvaluationStopReason.ACCESS_REVOKED, EvaluationStopReason.CONNECTION_CHANGED}


class EvaluationHalted(Exception):
    """The run cap refused a call: the cap is spent, the run was cancelled or it ended."""

    def __init__(self, reservation: CallReservation) -> None:
        super().__init__(reservation.value)
        self.reservation = reservation


class _Stop(Exception):
    def __init__(self, reason: EvaluationStopReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


class FailureCountingGateway:
    """Count failed provider calls. Their reserved cap slot is never refunded."""

    def __init__(self, inner: LlmGateway, failed: Callable[[], Awaitable[None]]) -> None:
        self._inner, self._failed = inner, failed

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        try:
            return await self._inner.complete(base_url, api_key, model, request)
        except AiAllowanceExceeded:
            raise  # refused by a policy before dispatch; nothing was sent
        except Exception:
            await self._failed()
            raise


class EvaluationExecution:
    def __init__(
        self,
        units: EvaluationUnitFactory,
        harness: EvaluationHarness,
        gateway: LlmGateway,
        cipher: SecretCipher,
        clock: Clock,
        accounting: AiUsageAccounting | None,
    ) -> None:
        self._units, self._harness, self._gateway = units, harness, gateway
        self._cipher, self._clock, self._accounting = cipher, clock, accounting

    async def execute(self, run_id: UUID) -> None:
        session: EvaluationSession | None = None
        try:
            prepared = await self._prepare(run_id)
            if prepared is None:
                return
            run, connection, api_key = prepared
            session = self._harness.open(
                run, connection, self._metered(run), api_key, lambda: self._admit(run.id)
            )
            outcome = await self._cases(run, session)
        except asyncio.CancelledError:
            await self._close(run_id, session, await self._cancelled_outcome(run_id))
            raise
        except _Stop as stop:
            outcome = (STOPPED, stop.reason)
        except EvaluationHalted as halted:
            outcome = _halted(halted.reservation)
        except AiAllowanceExceeded:
            outcome = (STOPPED, EvaluationStopReason.ALLOWANCE)
        except Exception as exc:
            # Exception text can quote provider or validation input; log only its type.
            log.warning("evaluation.run_failed", extra={"error": type(exc).__name__})
            outcome = (STOPPED, EvaluationStopReason.FAILED)
        await self._close(run_id, session, outcome)

    async def _cases(self, run: EvaluationRun, session: EvaluationSession) -> Outcome:
        for case_id in run.case_ids:
            summary = await session.evaluate(case_id)
            async with self._units() as unit:
                await self._recheck(unit, run, for_update=True)
                current = await unit.runs.record_case(
                    run.id, summary, self._clock.now() + RUN_LEASE
                )
                await unit.uow.commit()
            if current is None:
                return STOPPED, EvaluationStopReason.INTERRUPTED
            if current.cancel_requested:
                return EvaluationRunStatus.CANCELLED, None
        return EvaluationRunStatus.COMPLETED, None

    async def _prepare(
        self, run_id: UUID
    ) -> tuple[EvaluationRun, EvaluationConnection, str] | None:
        async with self._units() as unit:
            run = await unit.runs.get(run_id)
            if run is None or not run.active:
                return None
            profile = await self._recheck(unit, run)
        if run.cancel_requested:
            raise EvaluationHalted(CallReservation.CANCELLED)
        connection = EvaluationConnection(
            profile_id=profile.id,
            name=profile.name,
            model=profile.model,
            base_url=profile.base_url,
            provider=profile.provider,
            max_output_tokens=profile.max_output_tokens,
            temperature=profile.temperature,
            reasoning_effort=profile.reasoning_effort,
        )
        return run, connection, self._cipher.decrypt(profile.api_key_encrypted)

    async def _recheck(
        self, unit: EvaluationUnit, run: EvaluationRun, *, for_update: bool = False
    ) -> LlmProfile:
        if run.actor_id is None:
            raise _Stop(EvaluationStopReason.ACCESS_REVOKED)
        try:
            context = await unit.access.background(run.actor_id, None, for_update=for_update)
            require_admin(context.actor)
        except (Forbidden, Unauthenticated):
            raise _Stop(EvaluationStopReason.ACCESS_REVOKED) from None
        profile = await unit.profiles.get(run.profile_id)
        if profile is None or profile.config_hash != run.profile_fingerprint:
            raise _Stop(EvaluationStopReason.CONNECTION_CHANGED)
        return profile

    def _metered(self, run: EvaluationRun) -> LlmGateway:
        inner: LlmGateway = self._gateway
        if self._accounting is not None and run.actor_id is not None:
            inner = AllowanceLlmGateway(
                inner,
                self._accounting,
                attribution=AiAttribution.actor(run.actor_id),
                profile_id=run.profile_id,
                purpose_prefix="evaluation",
            )
        return FailureCountingGateway(inner, lambda: self._record_failure(run.id))

    async def _admit(self, run_id: UUID) -> None:
        """Consume one call of the durable cap before the call is recorded or sent."""
        async with self._units() as unit:
            reservation = await unit.runs.reserve_call(run_id, self._clock.now() + RUN_LEASE)
            await unit.uow.commit()
        if reservation is not CallReservation.RESERVED:
            raise EvaluationHalted(reservation)

    async def _record_failure(self, run_id: UUID) -> None:
        async with self._units() as unit:
            await unit.runs.record_failed_call(run_id)
            await unit.uow.commit()

    async def _cancelled_outcome(self, run_id: UUID) -> Outcome:
        with suppress(Exception):
            async with self._units() as unit:
                run = await unit.runs.get(run_id)
            if run is not None and run.cancel_requested:
                return EvaluationRunStatus.CANCELLED, None
        return STOPPED, EvaluationStopReason.INTERRUPTED

    async def _close(
        self, run_id: UUID, session: EvaluationSession | None, outcome: Outcome
    ) -> None:
        status, reason = outcome
        now = self._clock.now()
        artefact = None
        if session is not None and reason not in UNRETAINED:
            artefact = session.artefact(status, reason, now)
        try:
            async with self._units() as unit:
                await unit.runs.finish(run_id, status, reason, now, artefact)
                await unit.uow.commit()
        except Exception as exc:
            # The lease expires and a later start or cancel releases the slot.
            log.warning("evaluation.finish_failed", extra={"error": type(exc).__name__})


def _halted(reservation: CallReservation) -> Outcome:
    if reservation is CallReservation.CANCELLED:
        return EvaluationRunStatus.CANCELLED, None
    if reservation is CallReservation.CAP_REACHED:
        return STOPPED, EvaluationStopReason.CALL_CAP
    return STOPPED, EvaluationStopReason.INTERRUPTED


class EvaluationTasks:
    """In-process owner of running evaluation tasks; one run at a time is enforced in SQL."""

    def __init__(self, execute: Callable[[UUID], Coroutine[Any, Any, None]]) -> None:
        self._execute = execute
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    def launch(self, run_id: UUID) -> None:
        task = asyncio.create_task(self._execute(run_id), name=f"evaluation-{run_id}")
        self._tasks[run_id] = task
        task.add_done_callback(lambda _done: self._tasks.pop(run_id, None))

    def cancel(self, run_id: UUID) -> bool:
        task = self._tasks.get(run_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    def cancel_all(self) -> None:
        for task in list(self._tasks.values()):
            task.cancel()

    async def drain(self) -> None:
        """Wait for running evaluations; used by tests and on shutdown."""
        while self._tasks:
            running = dict(self._tasks)
            await asyncio.gather(*running.values(), return_exceptions=True)
            for run_id, task in running.items():
                if self._tasks.get(run_id) is task:
                    del self._tasks[run_id]
