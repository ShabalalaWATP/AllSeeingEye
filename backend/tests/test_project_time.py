"""Year-only temporal inclusion remains distinct from an exact occurrence date."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.feeds import EventQuery
from ase.application.reports.selection import select_evidence
from ase.application.reports.templates import TEMPLATES
from ase.application.research.collection import ResearchCollector
from ase.domain.evidence_time import EvidenceTimeBasis, evidence_time
from ase.domain.project_time import ProjectYearMatch, commitment_bounds, commitment_match
from ase.domain.research import ResearchBatch, ResearchQuery
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from feeds_helpers import NOW, make_event
from test_project_evidence import project


def test_unknown_year_has_no_comparison_bounds_or_implicit_retrieval_date():
    item = project(commitment_year=None)
    assert commitment_bounds(item) is None
    assert (
        commitment_match(item, datetime(2020, 1, 1, tzinfo=UTC), datetime(2021, 1, 1, tzinfo=UTC))
        is ProjectYearMatch.UNKNOWN
    )


def test_leap_year_and_half_open_boundaries():
    item = project(commitment_year=2020)
    start, end = commitment_bounds(item)
    assert (end - start).days == 366
    assert commitment_match(item, start, end) is ProjectYearMatch.WITHIN
    assert commitment_match(item, start - timedelta(days=1), start) is ProjectYearMatch.OUTSIDE
    assert commitment_match(item, end, end + timedelta(days=1)) is ProjectYearMatch.OUTSIDE
    assert (
        commitment_match(item, start + timedelta(days=59), start + timedelta(days=60))
        is ProjectYearMatch.POSSIBLE
    )


def test_equivalent_offset_bounds_and_last_supported_year():
    item = project(commitment_year=9998)
    start, end = commitment_bounds(item)
    assert end.year == 9999
    item = project(commitment_year=2020)
    start, end = commitment_bounds(item)
    offset = timezone(timedelta(hours=2))
    assert (
        commitment_match(item, start.astimezone(offset), end.astimezone(offset))
        is ProjectYearMatch.WITHIN
    )


@pytest.mark.parametrize(
    "start,end",
    [
        (datetime(2020, 1, 1), datetime(2021, 1, 1, tzinfo=UTC)),
        (datetime(2020, 1, 1, tzinfo=UTC), datetime(2020, 1, 1, tzinfo=UTC)),
        (datetime(2021, 1, 1, tzinfo=UTC), datetime(2020, 1, 1, tzinfo=UTC)),
    ],
)
def test_invalid_query_intervals_fail(start, end):
    with pytest.raises(ValueError):
        commitment_match(project(), start, end)


async def test_recorded_policy_collects_project_year_and_store_matches_same_interval():
    event = make_event().with_changes(project=project(commitment_year=2020), published_at=None)
    since, until = datetime(2020, 6, 1, tzinfo=UTC), datetime(2020, 6, 2, tzinfo=UTC)
    query = ResearchQuery("Project history", since, until, time_basis=EvidenceTimeBasis.RECORDED)

    class Provider:
        id = "fixture"
        name = "Project fixture"

        def supports(self, query):
            return True

        async def collect(self, query):
            return ResearchBatch(items=(event,))

    batch = await ResearchCollector((Provider(),)).collect(query)
    assert batch.items == (event,)
    assert "possibly overlap" in batch.attempts[0].explanation
    store = InMemoryEventStore()
    store.put(batch.items)
    assert store.query(
        EventQuery(since=since, until=until, time_basis=EvidenceTimeBasis.RECORDED)
    ) == [event]
    assert not store.query(EventQuery(since=since, until=until))
    selected = select_evidence(
        store,
        {},
        TEMPLATES["intsum"].strategy,
        now=NOW,
        since=since,
        until=until,
        time_basis=EvidenceTimeBasis.RECORDED,
    )
    assert len(selected.items) == 1
    assert selected.items[0].project.commitment_year == 2020
    assert selected.items[0].published_at is None
    assert evidence_time(event, EvidenceTimeBasis.RECORDED) is None
    receipt = ResearchReceipt.build(query, batch.attempts, 1)
    assert research_from_dict(research_to_dict(receipt)).time_basis is EvidenceTimeBasis.RECORDED
