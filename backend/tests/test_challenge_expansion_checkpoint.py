"""Durable v2 challenge lineage keeps every original citation label stable."""

import json
from dataclasses import replace
from datetime import timedelta

import pytest

from ase.application.report_jobs.budget import JobInterrupted
from ase.application.reports.challenge_expansion_checkpoint import (
    ExpansionPacket,
    ExpansionPlan,
    packet_from_dict,
    packet_to_dict,
    parent_digest,
    plan_from_dict,
    plan_to_dict,
    query_digest,
)
from ase.application.reports.production_checkpoint import ProductionSnapshot
from ase.application.reports.production_types import Totals
from ase.application.reports.selection import Selection
from ase.application.research.phase_ledger import new_phase_ledger
from ase.domain.research import ResearchMode, ResearchQuery
from report_checkpoint_helpers import checkpoint_setup
from report_job_helpers import NOW
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_snapshot_helpers import fixture_evidence


def first_packet():
    first = fixture_evidence()
    query = ResearchQuery("What changed?", NOW - timedelta(days=2), NOW, mode=ResearchMode.DETAILED)
    snapshot = ProductionSnapshot(Selection((first,), 0, 1), None, None, query, Totals())
    return snapshot, query


def test_exact_lineage_roundtrip_and_old_labels() -> None:
    snapshot, query = first_packet()
    plan = ExpansionPlan(
        parent_digest(snapshot), query_digest(query), "KJ1", ("contrary",), ("public",), "ready"
    )
    added = replace(snapshot.selection.items[0], label="E2", event_id="fresh-event")
    packet = ExpansionPacket(
        plan.parent, plan.fingerprint, (added,), None, "interrupted", "Safe stop"
    )
    assert plan_from_dict(json.loads(json.dumps(plan_to_dict(plan)))) == plan
    restored = packet_from_dict(json.loads(json.dumps(packet_to_dict(packet))))
    assert restored.added[0].label == "E2"
    assert snapshot.selection.items[0].label == "E1"
    assert restored.fingerprint == packet.fingerprint


def test_tampered_plan_or_oversized_packet_fails_closed() -> None:
    snapshot, query = first_packet()
    plan = ExpansionPlan(parent_digest(snapshot), query_digest(query), None, (), (), "unavailable")
    altered = plan_to_dict(plan)
    altered["source_ids"] = ["invented"] * 7
    with pytest.raises(ValueError, match="plan"):
        plan_from_dict(altered)
    packet = ExpansionPacket(plan.parent, plan.fingerprint, (), None, "unavailable", "No source")
    altered_packet = packet_to_dict(packet)
    altered_packet["parent"] = "not-a-hash"
    with pytest.raises(ValueError, match="expansion"):
        packet_from_dict(altered_packet)


async def test_plan_is_persisted_before_packet_and_resume_reuses_both(job_storage) -> None:
    snapshot, query = first_packet()
    _host, stored, checkpoints = await checkpoint_setup(
        job_storage, source_phase_ledger=new_phase_ledger(ResearchMode.DETAILED)
    )
    await checkpoints.save_collection(snapshot)
    plan = ExpansionPlan(
        parent_digest(snapshot), query_digest(query), "KJ1", ("contrary",), ("public",), "ready"
    )
    await checkpoints.save_expansion_plan(plan)
    restarted = type(checkpoints)(_host, stored.id, stored.lease_token)
    assert await restarted.load_expansion_plan() == plan
    assert await restarted.load_expansion_packet() is None
    packet = ExpansionPacket(plan.parent, plan.fingerprint, (), None, "unavailable", "No source")
    await restarted.save_expansion_packet(packet)
    again = type(checkpoints)(_host, stored.id, stored.lease_token)
    assert await again.load_expansion_packet() == packet
    with pytest.raises(JobInterrupted):
        await again.save_expansion_packet(replace(packet, reason="Conflicting result"))
