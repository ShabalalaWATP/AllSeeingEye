"""Offline report follow-through: selected originals use the frozen source allowance."""

import asyncio
from contextlib import suppress
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from ase.application.reports.original_followthrough import OriginalFollowThrough
from ase.application.reports.selection import Selection
from ase.application.research.original_phase import reserve_original
from ase.application.research.original_staging import StagedOriginalPassage
from ase.application.research.phase_ledger import (
    new_phase_ledger,
    reserve_operation,
    settle_operation,
)
from ase.application.research.phase_recovery import reconcile_open_operations
from ase.domain.evidence import EvidenceItem
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchMode, ResearchQuery
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from original_acquisition_support import (
    NOW,
    SOURCE,
    SPEC,
    Admission,
    Clock,
    Parser,
    event,
    policy,
    response,
)
from original_acquisition_support import (
    access as original_access,
)
from web_search_helpers import job


class Store:
    def __init__(self):
        self.event = event()

    def get(self, event_id):
        return self.event if event_id == self.event.id else None


class Staging:
    def __init__(self):
        self.rows = {}

    async def staged(self, job_id, event_id, now):
        row = self.rows.get((job_id, event_id))
        return row if row is not None and row.expires_at > now else None

    async def stage(self, *, job_id, event_id, evidence_label, document):
        row = StagedOriginalPassage(
            uuid4(), job_id, event_id, evidence_label, document, document.expires_at
        )
        self.rows[(job_id, event_id)] = row
        return row


class Checkpoints:
    def __init__(self):
        self.payload = {"source_phase_ledger": new_phase_ledger(ResearchMode.QUICK)}

    async def reserve_original_operation(self, *, mode, request_key):
        return reserve_operation(self.payload, mode=mode, phase="initial", request_key=request_key)

    async def settle_source_operation(
        self, *, mode, phase, request_key, elapsed_ms, retained_item_keys
    ):
        return settle_operation(
            self.payload,
            mode=mode,
            phase=phase,
            request_key=request_key,
            elapsed_ms=elapsed_ms,
            retained_item_keys=retained_item_keys,
        )


def setup(requirements=None, policies=None):
    report_job = job()
    report_job = replace(
        report_job,
        request=replace(
            report_job.request,
            research_web_search=False,
            canonical_requirements=requirements
            if requirements is not None
            else (IntelligenceRequirement("q1", "What does the issuer state?"),),
        ),
    )
    store = Store()
    selected = Selection(
        (
            EvidenceItem.from_event(
                "E1", store.event, NOW, source_name=SPEC.name, independence_key=""
            ),
        ),
        0,
        1,
    )
    query = ResearchQuery(
        report_job.request.question or "What changed?",
        NOW - timedelta(days=1),
        NOW,
        mode=ResearchMode.QUICK,
    )
    receipt = ResearchReceipt.build(
        query,
        (CollectionAttempt(SOURCE, SPEC.name, CollectionStatus.COMPLETED, 1),),
        1,
    )
    admission, clock, parser = Admission(), Clock(), Parser()
    staging, checkpoints = Staging(), Checkpoints()
    requests = []

    async def access():
        return original_access(report_job.actor.id)

    async def fetch(request):
        requests.append(request)
        return response()

    followthrough = OriginalFollowThrough(
        job_id=uuid4(),
        specs={SOURCE: SPEC},
        policies=policies if policies is not None else {SOURCE: policy()},
        admission=admission,
        current_access=access,
        parser=parser,
        clock=clock,
        fetch=fetch,
        staging=staging,
        checkpoints=checkpoints,
    )
    return report_job, store, selected, receipt, followthrough, requests, checkpoints, staging


def test_original_attempt_cap_counts_unknown_calls_and_keeps_replay_reason():
    payload = {"source_phase_ledger": new_phase_ledger(ResearchMode.QUICK)}
    first = reserve_original(payload, ResearchMode.QUICK, "original:first")
    assert first.dispatch
    assert reconcile_open_operations(payload, ResearchMode.QUICK)
    second = reserve_original(payload, ResearchMode.QUICK, "original:second")
    assert second.dispatch
    assert reconcile_open_operations(payload, ResearchMode.QUICK)
    replay = reserve_original(payload, ResearchMode.QUICK, "original:first")
    assert not replay.dispatch and replay.status == "unknown"
    denied = reserve_original(payload, ResearchMode.QUICK, "original:third")
    assert not denied.dispatch and denied.reason == "document_cap"


async def test_selected_original_is_staged_before_settlement_and_only_ref_is_frozen():
    report_job, store, selection, receipt, followthrough, requests, checkpoints, staging = setup()
    originals = await followthrough.collect(report_job, store, selection, receipt)
    assert len(requests) == 1
    assert originals[0].status == "acquired"
    assert originals[0].evidence_label == "E1"
    assert originals[0].passage_ref is not None
    assert len(staging.rows) == 1
    assert "Exact original passage." in await followthrough.context(originals)
    frozen = research_to_dict(replace(receipt, original_followup=originals))
    assert research_from_dict(frozen).original_followup == originals
    assert "Exact original passage." not in str(frozen)
    ledger = checkpoints.payload["source_phase_ledger"]["phases"]["initial"]["operations"]
    assert len(ledger) == 1
    assert next(iter(ledger.values()))["status"] == "settled"
    reused = await followthrough.collect(report_job, store, selection, receipt)
    assert reused[0].passage_ref == originals[0].passage_ref
    assert reused[0].transport_requests is None
    assert reused[0].transport_requests_reserved == 3
    assert len(requests) == 1


async def test_missing_policy_and_ambiguous_requirement_mapping_never_fetch():
    report_job, store, selection, receipt, followthrough, requests, checkpoints, _ = setup(
        policies={}
    )
    rows = await followthrough.collect(report_job, store, selection, receipt)
    assert rows[0].reason == "no_reviewed_policy"
    assert not requests
    assert not checkpoints.payload["source_phase_ledger"]["phases"]["initial"]["operations"]
    report_job, store, selection, receipt, followthrough, requests, _, _ = setup(
        requirements=(
            IntelligenceRequirement("q1", "First?"),
            IntelligenceRequirement("q2", "Second?"),
        )
    )
    rows = await followthrough.collect(report_job, store, selection, receipt)
    assert rows[0].reason == "requirement_mapping_unavailable"
    assert not requests


async def test_rejected_transport_keeps_headline_only_and_conservative_request_charge():
    report_job, store, selection, receipt, followthrough, requests, checkpoints, staging = setup()

    async def rejected(request):
        requests.append(request)
        return response(content_encoding="gzip")

    followthrough.fetch = rejected
    rows = await followthrough.collect(report_job, store, selection, receipt)
    assert rows[0].status == "headline_only"
    assert rows[0].reason == "compressed_response_not_permitted"
    assert rows[0].transport_requests is None
    assert rows[0].transport_requests_reserved == 3
    assert not staging.rows
    ledger = checkpoints.payload["source_phase_ledger"]["phases"]["initial"]["operations"]
    assert next(iter(ledger.values()))["status"] == "settled"


async def test_interrupted_fetch_is_unknown_and_cannot_dispatch_on_resume():
    report_job, store, selection, receipt, followthrough, requests, checkpoints, _ = setup()
    started = asyncio.Event()

    async def pending(request):
        requests.append(request)
        started.set()
        await asyncio.Event().wait()

    followthrough.fetch = pending
    task = asyncio.create_task(followthrough.collect(report_job, store, selection, receipt))
    await asyncio.wait_for(started.wait(), 1)
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    assert reconcile_open_operations(checkpoints.payload, ResearchMode.QUICK)
    rows = await followthrough.collect(report_job, store, selection, receipt)
    assert rows[0].reason == "source_operation_unknown"
    assert len(requests) == 1
