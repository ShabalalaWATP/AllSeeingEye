"""A saved expansion reuses its v2 evidence without replaying a source or model plan."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock

from ase.application.reports.challenge_expansion import expand_and_review
from ase.application.reports.challenge_expansion_checkpoint import (
    ExpansionPacket,
    ExpansionPlan,
    packet_from_dict,
    packet_to_dict,
    parent_digest,
    query_digest,
)
from ase.application.reports.drafting import Draft
from ase.application.reports.production_checkpoint import ProductionSnapshot
from ase.application.reports.production_types import Totals
from ase.application.reports.selection import Selection
from ase.domain.reports import parse_body
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchMode,
    ResearchQuery,
)
from ase.domain.research_records import ResearchReceipt
from feeds_helpers import make_event
from production_integration_helpers import production_job
from report_documents_helpers import document_records
from report_helpers import good_body
from report_job_helpers import NOW


class SavedExpansion:
    def __init__(self, plan, packet):
        self.plan, self.packet = plan, packet

    async def load_expansion_plan(self):
        return self.plan

    async def save_expansion_plan(self, _plan):
        raise AssertionError("Known model plan must be reused")

    async def load_expansion_packet(self):
        return self.packet

    async def save_expansion_packet(self, _packet):
        raise AssertionError("Known source packet must be reused")


class CollectingExpansion(SavedExpansion):
    def __init__(self, plan):
        super().__init__(plan, None)

    async def save_expansion_packet(self, packet):
        self.packet = packet


class FreshSource:
    def __init__(self):
        self.calls = 0

    async def collect_challenge_checkpointed(self, _query, _source_ids, operations, freeze):
        self.calls += 1
        batch = ResearchBatch(
            items=(make_event(title="A contrary observation", source_id="public"),),
            attempts=(CollectionAttempt("public", "Public", CollectionStatus.COMPLETED, 1),),
        )
        operations.evidence = await freeze(batch)
        operations.attempts = batch.attempts
        return batch


class MemoryPartial:
    def __init__(self):
        self.evidence = ()
        self.attempts = ()

    async def load_challenge_partial(self):
        return self.evidence, self.attempts


async def test_saved_v2_adds_new_label_without_mutating_v1(container, user):
    _, version = document_records()
    job = production_job(user, container.cipher)
    query = ResearchQuery("What changed?", NOW - timedelta(days=2), NOW, mode=ResearchMode.DETAILED)
    first = Selection(version.evidence, 0, len(version.evidence))
    snapshot = ProductionSnapshot(first, None, None, query, Totals())
    body = parse_body(good_body())
    plan = ExpansionPlan(
        parent_digest(snapshot), query_digest(query), "KJ1", ("contrary",), ("public",), "ready"
    )
    new_item = replace(first.items[0], label="E4", event_id="new-contrary-record")
    receipt = ResearchReceipt.build(
        query,
        (CollectionAttempt("public", "Public", CollectionStatus.COMPLETED, 1),),
        1,
    )
    packet = ExpansionPacket(
        plan.parent, plan.fingerprint, (new_item,), receipt, "attempted", "Fresh"
    )
    checkpoints = SavedExpansion(plan, packet)
    redraft = AsyncMock(return_value=Draft(body=body))

    async def no_profile(_role):
        return None

    outcome = await expand_and_review(
        job,
        Draft(body=body),
        snapshot,
        collection=None,
        source_operations=object(),
        checkpoints=checkpoints,
        profiles={},
        gateway=object(),
        cipher=container.cipher,
        profile_for=no_profile,
        totals=Totals(),
        redraft=redraft,
        progress=None,
    )
    assert tuple(item.label for item in outcome.selection.items) == ("E1", "E2", "E3", "E4")
    assert tuple(item.label for item in snapshot.selection.items) == ("E1", "E2", "E3")
    assert outcome.challenge.redrafted is True
    assert outcome.challenge.searches[0].selected_event_ids == ("new-contrary-record",)
    assert outcome.challenge.searches[1].status == "unavailable"
    redraft.assert_awaited_once()


async def test_live_challenge_saves_v2_and_does_not_collect_twice(container, user):
    _, version = document_records()
    job = production_job(user, container.cipher)
    query = ResearchQuery("What changed?", NOW - timedelta(days=2), NOW, mode=ResearchMode.DETAILED)
    snapshot = ProductionSnapshot(
        Selection(version.evidence, 0, len(version.evidence)), None, None, query, Totals()
    )
    body = parse_body(good_body())
    plan = ExpansionPlan(
        parent_digest(snapshot), query_digest(query), "KJ1", ("contrary",), ("public",), "ready"
    )
    checkpoints, source = CollectingExpansion(plan), FreshSource()

    async def no_profile(_role):
        return None

    args = {
        "collection": source,
        "source_operations": MemoryPartial(),
        "checkpoints": checkpoints,
        "profiles": {},
        "gateway": object(),
        "cipher": container.cipher,
        "profile_for": no_profile,
        "totals": Totals(),
        "redraft": AsyncMock(return_value=Draft(body=body)),
        "progress": None,
    }
    first = await expand_and_review(job, Draft(body=body), snapshot, **args)
    second = await expand_and_review(job, Draft(body=body), snapshot, **args)
    assert source.calls == 1
    assert checkpoints.packet.status == "attempted"
    assert packet_from_dict(packet_to_dict(checkpoints.packet)) == checkpoints.packet
    assert len(checkpoints.packet.added) == 1
    assert tuple(row.label for row in first.selection.items) == tuple(
        row.label for row in second.selection.items
    )
