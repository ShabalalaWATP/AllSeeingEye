"""Fresh-transaction, lease-fenced collection and section checkpoints for report workers."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.monthly_report_usage import reserve_new_call
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.ports.section_checkpoints import SectionCheckpoint, SectionCheckpoints
from ase.application.report_jobs.budget import JobInterrupted
from ase.application.report_jobs.views import refresh_summary
from ase.application.reports.production_checkpoint import (
    ProductionSnapshot,
    collection_from_dict,
    collection_to_dict,
)
from ase.application.research.original_phase import reserve_original
from ase.application.research.phase_ledger import (
    LEDGER_KEY,
    Phase,
    PhaseLedgerError,
    ReservationDecision,
    SettlementReceipt,
    abandon_operation,
    reserve_operation,
    settle_operation,
)
from ase.application.research.phase_recovery import reconcile_open_operations
from ase.container.report_job_expansion import ChallengeExpansionMixin
from ase.container.report_job_usage import settled_usage
from ase.domain.report_jobs import ReportJob, job_error
from ase.domain.research import ResearchMode
from ase.domain.subscription_monthly_budget import MonthlyBudgetPolicy

if TYPE_CHECKING:
    from ase.container import Container

LEASE_SECONDS = 45


class ReportJobCheckpoints(ChallengeExpansionMixin):
    def __init__(self, container: Container, job_id: UUID, lease_token: UUID) -> None:
        self.container, self.job_id, self.lease_token = container, job_id, lease_token
        self.source_phase_enabled = False
        self._lock = asyncio.Lock()
        self._sections = _Sections(self)

    def _leased(self, job: ReportJob | None) -> ReportJob:
        if (
            job is None
            or job.status != "running"
            or job.lease_token != self.lease_token
            or job.lease_until is None
            or job.lease_until <= self.container.clock.now()
        ):
            raise JobInterrupted()
        return job

    async def _authorised(self, session: AsyncSession, *, reset: bool = True) -> ReportJob:
        repository = SqlReportJobRepository(session)
        initial = self._leased(await repository.get(self.job_id))
        if reset:
            await session.rollback()
        await self.container.access_policy(session).background(
            initial.owner_id, initial.team_id, for_update=True
        )
        current = self._leased(await repository.get(self.job_id))
        await self.container.report_job_gate(session, current)
        return self._leased(current)

    async def _read(self) -> dict[str, Any]:
        async with (
            self._lock,
            self.container.source_admission.guard(),
            self.container.session_factory() as session,
        ):
            try:
                return deepcopy((await self._authorised(session)).payload)
            finally:
                await session.rollback()

    async def check(self) -> None:
        await self._read()

    async def _account(
        self, session: AsyncSession, job: ReportJob, payload: dict[str, Any]
    ) -> None:
        entries = settled_usage(job.payload, payload, job.owner_id, self.container.clock.now())
        usage = self.container.repositories(session).llm_usage
        for entry in entries:
            await usage.add(entry)

    async def mutate(self, callback: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        async with (
            self._lock,
            self.container.source_admission.guard(),
            self.container.session_factory() as session,
        ):
            try:
                job = await self._authorised(session)
                payload = deepcopy(job.payload)
                callback(payload)
                now = self.container.clock.now()
                await reserve_new_call(
                    session,
                    job,
                    payload,
                    now,
                    getattr(self.container, "monthly_budget_policy", MonthlyBudgetPolicy()),
                )
                refresh_summary(payload)
                await self.container.report_job_gate(session, replace(job, payload=payload))
                self._leased(job)
                await self._account(session, job, payload)
                self._leased(job)
                updated = await SqlReportJobRepository(session).checkpoint(
                    self.job_id,
                    expected_revision=job.revision,
                    lease_token=self.lease_token,
                    payload=payload,
                    stage=payload.get("stage", job.stage),
                    now=now,
                    lease_until=now + timedelta(seconds=LEASE_SECONDS),
                )
                if updated is None:
                    raise JobInterrupted()
                await session.commit()
                return updated.payload
            except BaseException:
                await session.rollback()
                raise

    async def load_collection(self) -> ProductionSnapshot | None:
        payload = await self._read()
        value = payload.get("collection")
        return collection_from_dict(value) if value is not None else None

    async def reconcile_open_source_operations(self, mode: ResearchMode) -> None:
        """Fence prior-lease operations before this worker can issue a new request."""
        enabled = False

        def reconcile(payload: dict[str, Any]) -> None:
            nonlocal enabled
            enabled = reconcile_open_operations(payload, mode)

        await self.mutate(reconcile)
        self.source_phase_enabled = enabled

    async def reserve_source_operation(
        self, *, mode: ResearchMode, phase: Phase, request_key: str
    ) -> ReservationDecision:
        """Commit a source allowance before the caller dispatches outbound work.

        Only jobs admitted with a frozen source-phase ledger use this port.
        A duplicate key never grants another dispatch, including after restart.
        """
        captured: list[ReservationDecision] = []

        def reserve(payload: dict[str, Any]) -> None:
            if LEDGER_KEY not in payload:
                raise PhaseLedgerError("Source-phase ledger is absent")
            captured.append(
                reserve_operation(payload, mode=mode, phase=phase, request_key=request_key)
            )

        await self.mutate(reserve)
        return captured[0]

    async def reserve_original_operation(
        self, *, mode: ResearchMode, request_key: str
    ) -> ReservationDecision:
        """Count every prior original attempt before charging the shared initial phase."""
        captured: list[ReservationDecision] = []

        def reserve(payload: dict[str, Any]) -> None:
            captured.append(reserve_original(payload, mode, request_key))

        await self.mutate(reserve)
        return captured[0]

    async def settle_source_operation(
        self,
        *,
        mode: ResearchMode,
        phase: Phase,
        request_key: str,
        elapsed_ms: int,
        retained_item_keys: tuple[str, ...] | list[str],
    ) -> SettlementReceipt:
        """Commit known elapsed time and admitted item keys after outbound work."""
        captured: list[SettlementReceipt] = []

        def settle(payload: dict[str, Any]) -> None:
            if LEDGER_KEY not in payload:
                raise PhaseLedgerError("Source-phase ledger is absent")
            captured.append(
                settle_operation(
                    payload,
                    mode=mode,
                    phase=phase,
                    request_key=request_key,
                    elapsed_ms=elapsed_ms,
                    retained_item_keys=retained_item_keys,
                )
            )

        await self.mutate(settle)
        return captured[0]

    async def abandon_source_operation(
        self, *, mode: ResearchMode, phase: Phase, request_key: str
    ) -> ReservationDecision:
        """Commit an unknown request without refund after lease-fenced recovery."""
        captured: list[ReservationDecision] = []

        def abandon(payload: dict[str, Any]) -> None:
            if LEDGER_KEY not in payload:
                raise PhaseLedgerError("Source-phase ledger is absent")
            captured.append(
                abandon_operation(payload, mode=mode, phase=phase, request_key=request_key)
            )

        await self.mutate(abandon)
        return captured[0]

    async def save_collection(self, snapshot: ProductionSnapshot) -> None:
        value = collection_to_dict(snapshot)

        def save(payload: dict[str, Any]) -> None:
            if payload.get("collection") is not None and payload["collection"] != value:
                raise JobInterrupted()
            payload["collection"] = value
            payload["stage"] = "drafting"

        await self.mutate(save)

    @property
    def section_checkpoints(self) -> SectionCheckpoints:
        return self._sections

    async def finish(
        self, session: AsyncSession, payload: dict[str, Any], needs_review: bool = False
    ) -> ReportJob:
        """Caller holds source guard and owns the final report transaction/rollback.

        Do not acquire the local lock here: a heartbeat may already hold it while
        waiting for the caller's source guard. The database lease still fences it.
        """
        job = await self._authorised(session, reset=False)
        payload = deepcopy(payload)
        payload["stage"] = "completed"
        refresh_summary(payload)
        await self.container.report_job_gate(session, replace(job, payload=payload))
        self._leased(job)
        await self._account(session, job, payload)
        self._leased(job)
        final = await SqlReportJobRepository(session).complete(
            self.job_id,
            expected_revision=job.revision,
            lease_token=self.lease_token,
            payload=payload,
            now=self.container.clock.now(),
            needs_review=needs_review,
        )
        if final is None:
            raise JobInterrupted()
        return final


class _Sections:
    def __init__(self, parent: ReportJobCheckpoints) -> None:
        self.parent = parent

    @staticmethod
    def _key(packet_digest: str, section_id: str) -> str:
        if (
            not re.fullmatch(r"[0-9a-f]{64}", packet_digest)
            or not 1 <= len(section_id.strip()) <= 120
            or len(section_id) > 120
            or any(ord(char) < 32 for char in section_id)
        ):
            raise JobInterrupted()
        return f"{packet_digest}:{section_id}"

    async def load(self, packet_digest: str, section_id: str) -> SectionCheckpoint | None:
        key = self._key(packet_digest, section_id)
        payload = await self.parent._read()
        sections = payload.get("sections", {})
        if type(sections) is not dict:
            raise JobInterrupted()
        value = sections.get(key)
        if value is None:
            return None
        if (
            type(value) is not dict
            or value.get("packet_digest") != packet_digest
            or value.get("section_id") != section_id
            or value.get("status") not in {"running", "completed", "split", "incomplete"}
        ):
            raise JobInterrupted()
        return SectionCheckpoint(value["status"], value.get("payload"), value.get("reason"))

    async def save(
        self, packet_digest: str, section_id: str, checkpoint: SectionCheckpoint
    ) -> None:
        key = self._key(packet_digest, section_id)
        if checkpoint.status not in {"running", "completed", "split", "incomplete"} or (
            checkpoint.payload is not None and type(checkpoint.payload) is not dict
        ):
            raise JobInterrupted()
        job_error(checkpoint.reason)
        value = {
            "packet_digest": packet_digest,
            "section_id": section_id,
            "status": checkpoint.status,
            "payload": deepcopy(checkpoint.payload),
            "reason": checkpoint.reason,
        }

        def save(payload: dict[str, Any]) -> None:
            sections = payload.setdefault("sections", {})
            if type(sections) is not dict:
                raise JobInterrupted()
            previous = sections.get(key)
            if previous is not None and type(previous) is not dict:
                raise JobInterrupted()
            if previous and previous.get("status") == "completed" and previous != value:
                raise JobInterrupted()
            sections[key] = value
            payload["current_packet"] = packet_digest
            payload["stage"] = (
                "summarising"
                if (checkpoint.payload or {}).get("kind") == "synthesis"
                else "drafting"
            )

        await self.parent.mutate(save)
