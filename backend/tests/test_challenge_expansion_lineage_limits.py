"""Large document, media and follow-up selections keep valid lineage without additions."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.application.reports.challenge_expansion_checkpoint import (
    ExpansionPacket,
    ExpansionPlan,
    parent_digest,
    query_digest,
    validate_lineage,
)
from ase.application.reports.production_checkpoint import ProductionSnapshot
from ase.application.reports.production_types import Totals
from ase.application.reports.selection import Selection
from ase.domain.research import ResearchMode, ResearchQuery
from report_job_helpers import NOW
from report_job_snapshot_helpers import fixture_evidence


def _setup(
    count: int, mode: ResearchMode = ResearchMode.DETAILED
) -> tuple[ProductionSnapshot, ExpansionPlan]:
    base = fixture_evidence()
    items = tuple(
        replace(base, label=f"E{index + 1}", event_id=f"original-{index}") for index in range(count)
    )
    query = ResearchQuery("What changed?", NOW - timedelta(days=2), NOW, mode=mode)
    snapshot = ProductionSnapshot(Selection(items, 0, count), None, None, query, Totals())
    plan = ExpansionPlan(
        parent_digest(snapshot), query_digest(query), "KJ1", ("contrary",), ("public",), "ready"
    )
    return snapshot, plan


def _added(first: int, count: int) -> tuple:
    base = fixture_evidence()
    return tuple(
        replace(base, label=f"E{first + index}", event_id=f"fresh-{index}")
        for index in range(count)
    )


@pytest.mark.parametrize("count", [49, 70, 100])
@pytest.mark.parametrize("status", ["unavailable", "attempted", "not_applicable"])
def test_empty_packet_over_final_limit_keeps_lineage(count: int, status: str) -> None:
    snapshot, plan = _setup(count)
    packet = ExpansionPacket(plan.parent, plan.fingerprint, (), None, status, "No additions")  # type: ignore[arg-type]
    validate_lineage(packet, plan, snapshot)


def test_advanced_follow_up_with_inherited_hundred_items_keeps_lineage() -> None:
    snapshot, plan = _setup(100, ResearchMode.ADVANCED)
    packet = ExpansionPacket(plan.parent, plan.fingerprint, (), None, "unavailable", "None")
    validate_lineage(packet, plan, snapshot)


@pytest.mark.parametrize(("count", "added"), [(48, 1), (49, 1), (45, 4), (100, 1)])
def test_additions_beyond_final_limit_are_rejected(count: int, added: int) -> None:
    snapshot, plan = _setup(count)
    packet = ExpansionPacket(
        plan.parent, plan.fingerprint, _added(count + 1, added), None, "attempted", "Fresh"
    )
    with pytest.raises(ValueError, match="lineage"):
        validate_lineage(packet, plan, snapshot)


def test_additions_within_the_remaining_allowance_are_accepted() -> None:
    snapshot, plan = _setup(45)
    packet = ExpansionPacket(
        plan.parent, plan.fingerprint, _added(46, 3), None, "attempted", "Fresh"
    )
    validate_lineage(packet, plan, snapshot)
