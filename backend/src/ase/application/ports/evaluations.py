"""Ports for administrator evaluation runs: durable run state and the packaged harness."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from ase.domain.evaluations import (
    EvaluationCaseInfo,
    EvaluationCaseSummary,
    EvaluationConnection,
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationStopReason,
)

if TYPE_CHECKING:
    from ase.application.access import AccessPolicy
    from ase.application.ports import UnitOfWork
    from ase.application.ports.llm import LlmGateway, LlmProfileRepository


class CallReservation(StrEnum):
    RESERVED = "reserved"
    CAP_REACHED = "cap_reached"
    CANCELLED = "cancelled"
    NOT_RUNNING = "not_running"


class EvaluationRunRepository(Protocol):
    async def add(self, run: EvaluationRun) -> None:
        """Insert a running run; raise Conflict if another run holds the active slot."""

    async def get(self, run_id: UUID) -> EvaluationRun | None: ...

    async def active(self) -> EvaluationRun | None: ...

    async def recent(self, limit: int) -> list[EvaluationRun]: ...

    async def reserve_call(self, run_id: UUID, lease_until: datetime) -> CallReservation:
        """Atomically consume one call of the cap; failed calls are never refunded."""

    async def record_failed_call(self, run_id: UUID) -> None: ...

    async def record_case(
        self, run_id: UUID, summary: EvaluationCaseSummary, lease_until: datetime
    ) -> EvaluationRun | None: ...

    async def request_cancel(self, run_id: UUID) -> None: ...

    async def finish(
        self,
        run_id: UUID,
        status: EvaluationRunStatus,
        reason: EvaluationStopReason | None,
        now: datetime,
        artefact: bytes | None,
    ) -> None:
        """Close a running run and release the active slot; finished runs are unchanged."""

    async def artefact(self, run_id: UUID) -> bytes | None: ...

    async def prune(self, keep: int) -> int:
        """Delete the oldest finished runs beyond ``keep``."""


@dataclass(frozen=True, slots=True)
class EvaluationUnit:
    """Repositories bound to one short transaction of background run work."""

    runs: EvaluationRunRepository
    profiles: LlmProfileRepository
    access: AccessPolicy
    uow: UnitOfWork


EvaluationUnitFactory = Callable[[], AbstractAsyncContextManager[EvaluationUnit]]


class EvaluationSession(Protocol):
    """One run's harness state: completed cases and recorded calls, kept in memory."""

    async def evaluate(self, case_id: str) -> EvaluationCaseSummary: ...

    def artefact(
        self,
        status: EvaluationRunStatus,
        reason: EvaluationStopReason | None,
        finished_at: datetime,
    ) -> bytes | None:
        """A bounded zip of results, review template and reports, free of credentials."""


class EvaluationHarness(Protocol):
    def catalogue(self) -> tuple[EvaluationCaseInfo, ...]: ...

    def open(
        self,
        run: EvaluationRun,
        connection: EvaluationConnection,
        gateway: LlmGateway,
        api_key: str,
        admit: Callable[[], Awaitable[None]],
    ) -> EvaluationSession:
        """``admit`` runs before each call is recorded or sent and may refuse it."""
