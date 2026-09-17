"""Historical retrieval relevance never invents timestamps or changes grades."""

from datetime import UTC, datetime, timedelta

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.selection import score, select_evidence
from ase.application.reports.templates import TEMPLATES
from ase.domain.evidence_time import EvidenceTimeBasis, evidence_time
from feeds_helpers import NOW, make_event
from test_project_evidence import project


def test_more_relevant_project_precedes_id_order_without_changing_evidence():
    base = make_event().with_changes(
        project=project(commitment_year=2020), published_at=None, summary=None
    )
    store = InMemoryEventStore()
    store.upsert(
        [
            # Two distinct records, each with its own link, so duplicate folding leaves
            # both in the pool and the ordering is what this test measures.
            base.with_changes(
                id="a",
                title="Airport runway resurfacing",
                content_hash="a",
                url="https://example.org/a",
            ),
            base.with_changes(
                id="z",
                title="Airport financing agreed",
                content_hash="z",
                url="https://example.org/z",
            ),
        ]
    )
    result = select_evidence(
        store,
        {},
        TEMPLATES["intsum"].strategy,
        now=NOW,
        since=datetime(2020, 1, 1, tzinfo=UTC),
        until=datetime(2021, 1, 1, tzinfo=UTC),
        time_basis=EvidenceTimeBasis.RECORDED,
        terms=("airport", "financing"),
    )
    assert [item.event_id for item in result.items] == ["z", "a"]
    assert all(item.published_at is None for item in result.items)
    assert {item.reliability for item in result.items} == {base.reliability}
    assert evidence_time(base, EvidenceTimeBasis.RECORDED) is None


def test_ordinary_undated_records_keep_existing_zero_recency_score():
    event = make_event().with_changes(published_at=None)
    assert score(event, NOW, timedelta(days=1)) == 0
    assert score(event, NOW, timedelta(days=1), EvidenceTimeBasis.RECORDED) == 0
