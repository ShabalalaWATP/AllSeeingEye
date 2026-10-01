"""SQL persistence for evaluation runs. Counters change through conditional UPDATEs."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.evaluation_run_models import EvaluationRunRow
from ase.application.ports.evaluations import CallReservation
from ase.domain.errors import Conflict
from ase.domain.evaluations import (
    EvaluationCaseSummary,
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationStopReason,
)

RUNNING = EvaluationRunStatus.RUNNING.value
MAX_ARTEFACT_BYTES = 8 * 1024 * 1024


def _summary(item: Mapping[str, Any]) -> EvaluationCaseSummary:
    return EvaluationCaseSummary(
        case_id=str(item["case_id"]),
        fingerprint=str(item["fingerprint"]),
        report_status=str(item["report_status"]),
        model_calls=int(item["model_calls"]),
        checks=dict(item["checks"]),
        prompt_tokens=item.get("prompt_tokens"),
        completion_tokens=item.get("completion_tokens"),
    )


def _summary_json(summary: EvaluationCaseSummary) -> dict[str, Any]:
    return {
        "case_id": summary.case_id,
        "fingerprint": summary.fingerprint,
        "report_status": summary.report_status,
        "model_calls": summary.model_calls,
        "checks": dict(summary.checks),
        "prompt_tokens": summary.prompt_tokens,
        "completion_tokens": summary.completion_tokens,
    }


def _domain(row: EvaluationRunRow) -> EvaluationRun:
    return EvaluationRun(
        id=row.id,
        actor_id=row.actor_id,
        profile_id=row.profile_id,
        profile_name=row.profile_name,
        model=row.model,
        profile_fingerprint=row.profile_fingerprint,
        case_ids=tuple(row.case_ids),
        case_fingerprints=dict(row.case_fingerprints),
        max_calls=row.max_calls,
        status=EvaluationRunStatus(row.status),
        created_at=row.created_at,
        lease_expires_at=row.lease_expires_at,
        stop_reason=EvaluationStopReason(row.stop_reason) if row.stop_reason else None,
        cancel_requested=row.cancel_requested,
        calls_reserved=row.calls_reserved,
        calls_failed=row.calls_failed,
        results=tuple(_summary(item) for item in row.results),
        finished_at=row.finished_at,
        has_artefact=row.has_artefact,
    )


class SqlEvaluationRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, run: EvaluationRun) -> None:
        self._session.add(
            EvaluationRunRow(
                id=run.id,
                actor_id=run.actor_id,
                profile_id=run.profile_id,
                profile_name=run.profile_name[:80],
                model=run.model,
                profile_fingerprint=run.profile_fingerprint,
                case_ids=list(run.case_ids),
                case_fingerprints=dict(run.case_fingerprints),
                max_calls=run.max_calls,
                status=run.status.value,
                active_slot=1 if run.active else None,
                cancel_requested=run.cancel_requested,
                calls_reserved=run.calls_reserved,
                calls_failed=run.calls_failed,
                results=[_summary_json(item) for item in run.results],
                has_artefact=False,
                created_at=run.created_at,
                lease_expires_at=run.lease_expires_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError:
            # The unique active slot: another process started a run first.
            raise Conflict("An evaluation run is already in progress.") from None

    async def get(self, run_id: UUID) -> EvaluationRun | None:
        row = await self._session.get(EvaluationRunRow, run_id, populate_existing=True)
        return _domain(row) if row is not None else None

    async def active(self) -> EvaluationRun | None:
        row = await self._session.scalar(
            select(EvaluationRunRow).where(EvaluationRunRow.active_slot == 1)
        )
        return _domain(row) if row is not None else None

    async def recent(self, limit: int) -> list[EvaluationRun]:
        rows = await self._session.scalars(
            select(EvaluationRunRow)
            .order_by(EvaluationRunRow.created_at.desc(), EvaluationRunRow.id)
            .limit(limit)
        )
        return [_domain(row) for row in rows]

    async def reserve_call(self, run_id: UUID, lease_until: datetime) -> CallReservation:
        table = EvaluationRunRow
        result = await self._session.execute(
            update(table)
            .where(
                table.id == run_id,
                table.status == RUNNING,
                table.cancel_requested.is_(False),
                table.calls_reserved < table.max_calls,
            )
            .values(calls_reserved=table.calls_reserved + 1, lease_expires_at=lease_until)
            .execution_options(synchronize_session=False)
        )
        if _rowcount(result) == 1:
            return CallReservation.RESERVED
        run = await self.get(run_id)
        if run is None or not run.active:
            return CallReservation.NOT_RUNNING
        if run.cancel_requested:
            return CallReservation.CANCELLED
        return CallReservation.CAP_REACHED

    async def record_failed_call(self, run_id: UUID) -> None:
        table = EvaluationRunRow
        await self._session.execute(
            update(table)
            .where(table.id == run_id, table.calls_failed < table.calls_reserved)
            .values(calls_failed=table.calls_failed + 1)
            .execution_options(synchronize_session=False)
        )

    async def record_case(
        self, run_id: UUID, summary: EvaluationCaseSummary, lease_until: datetime
    ) -> EvaluationRun | None:
        row = await self._session.get(
            EvaluationRunRow, run_id, populate_existing=True, with_for_update=True
        )
        if row is None or row.status != RUNNING:
            return None
        row.results = [*row.results, _summary_json(summary)]
        row.lease_expires_at = lease_until
        await self._session.flush()
        return _domain(row)

    async def request_cancel(self, run_id: UUID) -> None:
        await self._session.execute(
            update(EvaluationRunRow)
            .where(EvaluationRunRow.id == run_id, EvaluationRunRow.status == RUNNING)
            .values(cancel_requested=True)
            .execution_options(synchronize_session=False)
        )

    async def finish(
        self,
        run_id: UUID,
        status: EvaluationRunStatus,
        reason: EvaluationStopReason | None,
        now: datetime,
        artefact: bytes | None,
    ) -> None:
        if status is EvaluationRunStatus.RUNNING:
            raise ValueError("A finished run needs a final status.")
        kept = artefact if artefact is not None and len(artefact) <= MAX_ARTEFACT_BYTES else None
        await self._session.execute(
            update(EvaluationRunRow)
            .where(EvaluationRunRow.id == run_id, EvaluationRunRow.status == RUNNING)
            .values(
                status=status.value,
                stop_reason=reason.value if reason else None,
                active_slot=None,
                lease_expires_at=None,
                finished_at=now,
                artefact=kept,
                has_artefact=kept is not None,
            )
            .execution_options(synchronize_session=False)
        )

    async def artefact(self, run_id: UUID) -> bytes | None:
        content: bytes | None = await self._session.scalar(
            select(EvaluationRunRow.artefact).where(EvaluationRunRow.id == run_id)
        )
        return content

    async def prune(self, keep: int) -> int:
        kept = (
            select(EvaluationRunRow.id)
            .order_by(EvaluationRunRow.created_at.desc(), EvaluationRunRow.id)
            .limit(max(keep, 0))
        )
        result = await self._session.execute(
            delete(EvaluationRunRow)
            .where(EvaluationRunRow.status != RUNNING, EvaluationRunRow.id.not_in(kept))
            .execution_options(synchronize_session=False)
        )
        return _rowcount(result)


def _rowcount(result: object) -> int:
    return result.rowcount if isinstance(result, CursorResult) else 0
