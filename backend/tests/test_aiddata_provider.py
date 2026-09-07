"""Native local project collection preserves meaning and explicit query scope."""

from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import pytest

from ase.adapters.research_records.aiddata_provider import AidDataProvider
from ase.adapters.research_records.aiddata_records import SOURCE_ID
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.feeds import EventQuery
from ase.application.reports.request import ReportRequest
from ase.application.reports.research import collect_report_evidence
from ase.application.research.challenge_collection import collect_challenges
from ase.application.research.service import ResearchCollectionService
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.project_time import MAX_PROJECT_INTERVAL
from ase.domain.research import CollectionStatus, ResearchMode, ResearchQuery
from feeds_helpers import make_event
from test_aiddata_search import END, START, catalogue
from test_research_area import area


def query(**changes):
    return ResearchQuery(
        **{
            "question": "Airport project commitments",
            "since": START,
            "until": END,
            "terms": ("airport",),
            "country_iso": "LA",
            "source_ids": (SOURCE_ID,),
            "time_basis": EvidenceTimeBasis.RECORDED,
        }
        | changes
    )


def provider(path):
    return AidDataProvider(path, SimpleNamespace(now=lambda: END), {"LAO": "LA"})


async def test_challenge_preserves_explicit_project_source_selection(tmp_path):
    native = provider(catalogue(tmp_path))
    batches = await collect_challenges((query(),), lambda request: [native])
    assert len(batches[0].items) == 1
    assert batches[0].attempts[0].status is CollectionStatus.COMPLETED


async def test_provider_admits_exact_project_area_and_does_not_use_its_envelope(tmp_path):
    native = provider(catalogue(tmp_path))
    inside = query(area=area([[[0, 0], [1, 0], [1, 1], [0, 0]]]))
    assert native.supports_area(inside)
    result = await ResearchCollectionService(lambda request: [native]).collect(inside)
    assert len(result.items) == 1
    assert result.plan.area == inside.area
    outside = query(area=area([[[0, 0.8], [0.1, 0.8], [0.1, 0.9], [0, 0.8]]]))
    assert not (await native.collect(outside)).items


async def test_project_history_does_not_import_unsolicited_live_context(tmp_path):
    live = InMemoryEventStore()
    live.upsert([make_event().with_changes(published_at=START, country_iso="LA")])
    native = provider(catalogue(tmp_path))
    request = ReportRequest(
        "ask",
        country_iso="LA",
        research_mode=ResearchMode.QUICK,
        research_time_basis=EvidenceTimeBasis.RECORDED,
        research_since=START,
        research_until=END,
    )
    private, _ = await collect_report_evidence(
        query(),
        request,
        ResearchCollectionService(lambda request: [native]),
        InMemoryEventStore,
        live,
    )
    assert {item.source_id for item in private.query(EventQuery(limit=10))} == {SOURCE_ID}
    assert live.stats().total == 1


async def test_native_catalogue_becomes_attributed_undated_project_evidence(tmp_path):
    batch = await provider(catalogue(tmp_path)).collect(query())
    assert batch.attempts[0].status is CollectionStatus.COMPLETED
    assert "No query was sent" in batch.attempts[0].explanation
    (event,) = batch.items
    assert event.published_at is None and event.observed_at == END
    assert event.country_iso == "LA"
    assert event.project.commitment_year == 2011
    assert event.geometry is not None
    assert dict(event.attributes)["aiddata_amount_constant_usd_2021"] == "123.5"
    assert "constant 2021 USD" in event.summary
    assert "not a payment" in event.summary


@pytest.mark.parametrize(
    "changes",
    [
        {"source_ids": None},
        {"country_iso": "GB"},
        {"time_basis": EvidenceTimeBasis.PUBLICATION},
    ],
)
async def test_unsupported_requests_do_not_open_catalogue(changes):
    result = await provider(None).collect(query(**changes))
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not result.items


async def test_missing_catalogue_is_unavailable_not_empty():
    result = await provider(None).collect(query())
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE


def test_preview_and_report_share_exact_historical_interval_ceiling():
    end = START + MAX_PROJECT_INTERVAL
    assert query(until=end).until == end
    request = ReportRequest(
        "briefing",
        research_mode=ResearchMode.QUICK,
        research_time_basis=EvidenceTimeBasis.RECORDED,
        research_since=START,
        research_until=end,
    )
    assert request.effective_time_basis is EvidenceTimeBasis.RECORDED
    with pytest.raises(ValueError):
        query(until=end + timedelta(microseconds=1))
    with pytest.raises(ValueError):
        replace(request, research_until=end + timedelta(microseconds=1))
    with pytest.raises(ValueError):
        replace(request, window_hours=24)
    with pytest.raises(ValueError):
        replace(request, research_time_basis=EvidenceTimeBasis.PUBLICATION)
