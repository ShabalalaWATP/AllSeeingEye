"""A restarted report cannot redispatch a reserved source task or reclaim unknown time."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.request import ReportRequest
from ase.application.reports.research import collect_report_evidence_with_query
from ase.application.research.collection import ResearchCollector
from ase.application.research.phase_ledger import (
    LEDGER_KEY,
    Phase,
    ReservationDecision,
    SettlementReceipt,
    new_phase_ledger,
    reserve_operation,
    settle_operation,
)
from ase.application.research.phase_recovery import reconcile_open_operations
from ase.application.research.reserved_collection import source_item_key
from ase.application.research.service import ResearchCollectionService
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchMode, ResearchQuery
from report_checkpoint_helpers import checkpoint_setup, current
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_service_helpers import service_environment as _service_environment  # noqa: F401
from test_allocated_plan import REQUIREMENTS, _context, _query
from test_research_collection import QUERY, Provider, event


@dataclass
class MemoryOperations:
    payload: dict[str, Any] = field(
        default_factory=lambda: {LEDGER_KEY: new_phase_ledger(ResearchMode.QUICK)}
    )
    source_phase_enabled: bool = True

    async def reserve_source_operation(
        self, *, mode: ResearchMode, phase: Phase, request_key: str
    ) -> ReservationDecision:
        return reserve_operation(self.payload, mode=mode, phase=phase, request_key=request_key)

    async def settle_source_operation(
        self,
        *,
        mode: ResearchMode,
        phase: Phase,
        request_key: str,
        elapsed_ms: int,
        retained_item_keys: tuple[str, ...],
    ) -> SettlementReceipt:
        return settle_operation(
            self.payload,
            mode=mode,
            phase=phase,
            request_key=request_key,
            elapsed_ms=elapsed_ms,
            retained_item_keys=retained_item_keys,
        )


@dataclass
class GuardedProvider(Provider):
    operations: MemoryOperations | None = None
    interrupt: bool = False

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        assert self.operations is not None
        ledger = self.operations.payload[LEDGER_KEY]
        assert any(
            row["status"] == "open" for row in ledger["phases"]["initial"]["operations"].values()
        )
        if self.interrupt:
            self.called += 1
            raise asyncio.CancelledError()
        return await super().collect(query)


async def test_settled_source_is_not_redispatched_after_json_resume() -> None:
    operations = MemoryOperations()
    provider = GuardedProvider(
        "alpha",
        ResearchBatch(items=(event("current"), event("old", QUERY.since - timedelta(seconds=1)))),
        operations=operations,
    )
    first = await ResearchCollector((provider,)).collect(QUERY, source_operations=operations)
    assert [item.id for item in first.items] == ["current"]
    assert provider.called == 1
    record = next(iter(operations.payload[LEDGER_KEY]["phases"]["initial"]["operations"].values()))
    assert record["status"] == "settled"
    assert record["retained_keys"] == [source_item_key("current")]
    assert 0 <= record["charged_ms"] <= record["allowance_ms"]

    restored = MemoryOperations(json.loads(json.dumps(operations.payload)))
    provider.operations = restored
    assert reconcile_open_operations(restored.payload, QUERY.mode)
    resumed = await ResearchCollector((provider,)).collect(QUERY, source_operations=restored)
    assert provider.called == 1
    assert resumed.items == ()
    assert resumed.attempts[0].status is CollectionStatus.NOT_COLLECTED
    assert "cannot be replayed" in resumed.attempts[0].explanation


async def test_open_operation_is_debited_then_next_task_can_run_after_resume() -> None:
    operations = MemoryOperations()
    first = GuardedProvider("alpha", operations=operations, interrupt=True)
    next_source = GuardedProvider("bravo", operations=operations)
    with pytest.raises(asyncio.CancelledError):
        await ResearchCollector((first, next_source)).collect(QUERY, source_operations=operations)
    saved = json.loads(json.dumps(operations.payload))
    open_record = next(iter(saved[LEDGER_KEY]["phases"]["initial"]["operations"].values()))
    assert open_record["status"] == "open"

    restored = MemoryOperations(saved)
    first.operations = next_source.operations = restored
    assert reconcile_open_operations(restored.payload, QUERY.mode)
    recovered = next(iter(restored.payload[LEDGER_KEY]["phases"]["initial"]["operations"].values()))
    assert recovered["status"] == "unknown"
    first.interrupt = False
    resumed = await ResearchCollector((first, next_source)).collect(
        QUERY, source_operations=restored
    )
    assert first.called == 1 and next_source.called == 1
    assert [row.status for row in resumed.attempts] == [
        CollectionStatus.NOT_COLLECTED,
        CollectionStatus.EMPTY,
    ]
    records = restored.payload[LEDGER_KEY]["phases"]["initial"]["operations"]
    assert sum(row["charged_ms"] for row in records.values()) >= 12_000


def test_old_job_without_source_ledger_retains_legacy_path() -> None:
    payload: dict[str, Any] = {"collection": None}
    assert not reconcile_open_operations(payload, ResearchMode.QUICK)
    assert payload == {"collection": None}


async def test_admitted_research_job_starts_with_frozen_source_phase_limits(service_env) -> None:
    request = ReportRequest("ask", question="What changed?", research_mode=ResearchMode.DETAILED)
    async with service_env.service() as (service, deps):
        candidate = await service.prepare_candidate(service_env.user, uuid4(), request)
        admitted = await service.admit_prepared(
            service_env.user, candidate, check_session=AsyncMock()
        )
        await deps.session.commit()
    async with service_env.factory() as session:
        persisted = await SqlReportJobRepository(session).get(admitted.id)
    assert persisted is not None
    ledger = candidate.payload[LEDGER_KEY]
    assert ledger == new_phase_ledger(ResearchMode.DETAILED)
    assert persisted.payload[LEDGER_KEY] == ledger
    assert ledger["phases"]["initial"]["limits"]["operations"] == 20
    assert ledger["phases"]["challenge"]["limits"]["operations"] == 4


async def test_report_collection_uses_checkpointed_source_port() -> None:
    provider = GuardedProvider("alpha", operations=MemoryOperations())
    operations = provider.operations
    assert operations is not None
    query = _query()
    request = ReportRequest(
        "ask",
        question=query.question,
        research_mode=ResearchMode.QUICK,
        canonical_requirements=REQUIREMENTS,
    )

    async def load(_ids: tuple[str, ...]):
        return _context((provider,))

    service = ResearchCollectionService(lambda _: (provider,), allocation_loader=load)
    _store, receipt, _effective = await collect_report_evidence_with_query(
        query,
        request,
        service,
        InMemoryEventStore,
        InMemoryEventStore(),
        source_operations=operations,
    )
    assert provider.called == 1
    assert receipt.attempts[0].status is CollectionStatus.EMPTY
    assert len(operations.payload[LEDGER_KEY]["phases"]["initial"]["operations"]) == 1


async def test_lease_fenced_checkpoint_restart_marks_open_source_unknown(job_storage) -> None:
    host, stored, adapter = await checkpoint_setup(
        job_storage, **{LEDGER_KEY: new_phase_ledger(ResearchMode.QUICK)}
    )
    await adapter.reconcile_open_source_operations(ResearchMode.QUICK)
    assert adapter.source_phase_enabled
    first = await adapter.reserve_source_operation(
        mode=ResearchMode.QUICK, phase="initial", request_key="pass:1:source"
    )
    assert first.dispatch
    persisted = await current(host, stored.id)
    assert (
        persisted.payload[LEDGER_KEY]["phases"]["initial"]["operations"]["pass:1:source"]["status"]
        == "open"
    )

    restarted = type(adapter)(host, stored.id, stored.lease_token)
    await restarted.reconcile_open_source_operations(ResearchMode.QUICK)
    replay = await restarted.reserve_source_operation(
        mode=ResearchMode.QUICK, phase="initial", request_key="pass:1:source"
    )
    assert not replay.dispatch and replay.status == "unknown"
    persisted = await current(host, stored.id)
    assert (
        persisted.payload[LEDGER_KEY]["phases"]["initial"]["operations"]["pass:1:source"][
            "charged_ms"
        ]
        == first.allowance_ms
    )
