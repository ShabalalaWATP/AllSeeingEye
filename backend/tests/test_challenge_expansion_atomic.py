"""Settled challenge evidence survives a restart before v2 publication."""

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta

from ase.application.reports.challenge_expansion_checkpoint import (
    ExpansionPacket,
    ExpansionPlan,
    parent_digest,
    query_digest,
)
from ase.application.reports.production_checkpoint import ProductionSnapshot, collection_to_dict
from ase.application.reports.production_types import Totals
from ase.application.reports.selection import Selection
from ase.application.research.phase_ledger import LEDGER_KEY, new_phase_ledger, reserve_operation
from ase.container.report_job_expansion import ChallengeExpansionMixin
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchMode, ResearchQuery
from ase.domain.research_records import ResearchReceipt
from report_documents_helpers import document_records
from report_job_helpers import NOW


class MemoryCheckpoint(ChallengeExpansionMixin):
    def __init__(self, payload):
        self.payload = payload

    async def _read(self):
        return deepcopy(self.payload)

    async def mutate(self, callback):
        candidate = deepcopy(self.payload)
        callback(candidate)
        self.payload = candidate
        return candidate


async def test_settlement_commits_selected_record_with_ledger_before_v2() -> None:
    _, version = document_records()
    query = ResearchQuery("What changed?", NOW - timedelta(days=2), NOW, mode=ResearchMode.DETAILED)
    selection = Selection(version.evidence, 0, len(version.evidence))
    snapshot = ProductionSnapshot(selection, None, None, query, Totals())
    plan = ExpansionPlan(
        parent_digest(snapshot),
        query_digest(query),
        "KJ1",
        ("contrary",),
        ("public",),
        "ready",
    )
    first = MemoryCheckpoint(
        {
            "collection": collection_to_dict(snapshot),
            LEDGER_KEY: new_phase_ledger(query.mode),
        }
    )
    await first.save_expansion_plan(plan)
    key = "challenge:" + "a" * 64
    reserve_operation(first.payload, mode=query.mode, phase="challenge", request_key=key)
    item = replace(selection.items[0], label="E4", event_id="fresh-opposition")
    receipt = CollectionAttempt(
        "public", "Public", CollectionStatus.COMPLETED, 1, task_id="public-task"
    )
    await first.settle_challenge_operation(
        mode=query.mode,
        request_key=key,
        elapsed_ms=21,
        evidence=(item,),
        attempt=receipt,
    )

    restarted = MemoryCheckpoint(deepcopy(first.payload))
    assert "challenge_expansion_packet" not in restarted.payload
    evidence, attempts = await restarted.load_challenge_partial()
    assert evidence == (item,)
    assert attempts[0].status is CollectionStatus.COMPLETED
    operation = restarted.payload[LEDGER_KEY]["phases"]["challenge"]["operations"][key]
    assert operation["status"] == "settled"
    assert operation["retained_keys"]
    packet = ExpansionPacket(
        plan.parent,
        plan.fingerprint,
        evidence,
        ResearchReceipt.build(query, attempts, len(evidence)),
        "attempted",
        "Fresh source requests were attempted.",
    )
    await restarted.save_expansion_packet(packet)
    assert await restarted.load_expansion_packet() == packet
