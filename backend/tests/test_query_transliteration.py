"""Operator transliteration executes real fixture adapters within existing collection budgets."""

import json
from dataclasses import replace

import httpx
import pytest

from ase.adapters.feeds.rss import RssOptions
from ase.adapters.research.news import GoogleNewsResearchProvider
from ase.adapters.research_records.company import SecSubmissionsProvider
from ase.api.schemas_research_plan import ResearchPlanIn
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import TEMPLATES
from ase.application.research.collection import CollectionBudget, ResearchCollector
from ase.domain.research import CollectionStatus, ResearchMode
from ase.domain.research_plan import QueryVariant
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from research_feed_helpers import CLOCK, QUERY, PublicFeed, item, rss
from research_records_helpers import RecordService, submissions
from test_candidate_registry_routing import candidate_query
from test_research_plan import Provider
from test_rss import connector


def variant():
    return QueryVariant(
        "en",
        ("Moskva",),
        "transliteration",
        ("Москва",),
        "Cyrl",
        "Latn",
        "Operator transliteration v1",
    )


async def test_actual_transliterated_http_terms_and_frozen_regeneration(monkeypatch):
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item(title="Moskva report"))))
    provider = GoogleNewsResearchProvider(feed.http, CLOCK, "en")
    query = replace(
        QUERY, terms=("Москва",), query_variants=(variant(),), source_ids=(provider.id,)
    )
    result = await ResearchCollector([provider]).collect(query)
    await feed.http.aclose()
    assert len(feed.requests) == 1
    assert "Moskva" in str(feed.requests[0].url)
    assert "Москва" not in str(feed.requests[0].url) and query.question not in str(
        feed.requests[0].url
    )
    assert len(result.items) == 1 and result.attempts[0].query_variant == variant()
    assert result.plan.tasks[0].query_variant == variant()
    receipt = ResearchReceipt.build(query, result.attempts, 1, result.plan)
    restored = research_from_dict(json.loads(json.dumps(research_to_dict(receipt))))
    assert restored == receipt
    request = ReportRequest(
        "ask",
        research_mode=ResearchMode.QUICK,
        research_terms=query.terms,
        research_query_variants=query.query_variants,
    )
    assert ReportRequest.from_scope(
        "ask", report_scope(request, TEMPLATES["ask"])
    ).research_query_variants == (variant(),)


async def test_transliteration_selection_and_shared_request_budget():
    providers = [Provider(f"source{i}") for i in range(8)]
    query = replace(QUERY, terms=("Москва",), query_variants=(variant(),))
    result = await ResearchCollector(providers).collect(
        query, budget=CollectionBudget(2, 45, 12, 200)
    )
    assert sum(len(provider.queries) for provider in providers) == 2
    assert all(q.terms == ("Moskva",) for provider in providers for q in provider.queries)
    assert all(
        attempt.status == CollectionStatus.BUDGET_EXHAUSTED for attempt in result.attempts[2:]
    )


def test_preflight_rejects_false_original_link_and_missing_transliteration_method():
    with pytest.raises(ValueError):
        ResearchPlanIn.model_validate(
            {
                "question": "q",
                "since": QUERY.since,
                "until": QUERY.until,
                "terms": ["other"],
                "query_variants": [
                    {
                        "language": "en",
                        "terms": ["Moskva"],
                        "kind": "transliteration",
                        "original_terms": ["Москва"],
                        "source_script": "Cyrl",
                        "target_script": "Latn",
                        "method": "operator",
                    }
                ],
            }
        )
    with pytest.raises(ValueError):
        QueryVariant("en", ("Moskva",), "transliteration", ("Москва",))


async def test_atom_updated_never_substitutes_publication(monkeypatch):
    xml = (
        "<feed><entry><id>1</id><title>Moskva</title>"
        "<updated>2026-09-05T10:00:00Z</updated>"
        "<published>2020-01-01T00:00:00Z</published>"
        '<link href="https://publisher.example/1" /></entry></feed>'
    )
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=xml))
    provider = GoogleNewsResearchProvider(feed.http, CLOCK, "en")
    result = await provider.collect(QUERY)
    await feed.http.aclose()
    assert result.items == ()


async def test_registry_subject_and_task_receipt_ignore_baseline_transliteration(monkeypatch):
    service = RecordService(monkeypatch, submissions())
    provider = SecSubmissionsProvider(service.http, CLOCK)
    query = candidate_query(provider.id, terms=("Москва",), query_variants=(variant(),))
    result = await ResearchCollector([provider]).collect(query)
    await service.http.aclose()
    task = next(row for row in result.plan.tasks if row.purpose == "disambiguation")
    attempt = next(row for row in result.attempts if row.purpose == "disambiguation")
    assert task.registry_lookup.subject == "CIK:0000001234"
    assert task.terms == () and task.query_variant is None and attempt.query_variant is None
    assert any("CIK0000001234.json" in str(request.url) for request in service.requests)


async def test_recent_modifications_do_not_displace_actual_new_publications_at_feed_cap(
    monkeypatch,
):

    old = "".join(
        f"<entry><id>old{i}</id><title>Old</title><updated>2026-09-06T12:00:00Z</updated>"
        "<published>2020-01-01T00:00:00Z</published></entry>"
        for i in range(200)
    )
    newest = (
        "<entry><id>new</id><title>New</title><updated>2026-09-05T12:00:00Z</updated>"
        "<published>2026-09-05T12:00:00Z</published></entry>"
    )
    events = await connector(
        "<feed>" + old + newest + "</feed>", RssOptions(newest_first=True)
    ).fetch()
    assert len(events) == 200 and events[0].title == "New"
    assert events[1].published_at.year == 2020
    assert {row.role for row in events[1].source_dates} == {"publication", "modification"}


async def test_dublin_core_lifecycle_date_cannot_qualify_publication_recency(monkeypatch):
    xml = (
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" xmlns:other="urn:unrelated">'
        "<item><guid>generic</guid><title>Moskva generic</title>"
        "<dc:date>2026-09-05T10:00:00Z</dc:date></item>"
        "<item><guid>issued</guid><title>Moskva issued</title>"
        "<dc:date>2026-09-06T10:00:00Z</dc:date>"
        "<dcterms:issued>2026-09-05T10:00:00Z</dcterms:issued></item>"
        "<item><guid>foreign</guid><title>Moskva foreign</title>"
        "<other:issued>2026-09-05T10:00:00Z</other:issued>"
        "<other:date>2026-09-05T10:00:00Z</other:date></item></rdf:RDF>"
    )
    events = await connector(xml, RssOptions(newest_first=True)).fetch()
    assert events[0].title == "Moskva issued"
    assert events[0].source_dates[0].field == "{http://purl.org/dc/terms/}issued"
    assert events[0].source_dates[0].role == "publication"
    assert events[1].published_at is None
    assert events[1].source_dates[0].role == "unspecified"
    assert events[1].source_dates[0].value is not None
    assert events[2].published_at is None
    assert all(row.calendar == "unknown" for row in events[2].source_dates)
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=xml))
    provider = GoogleNewsResearchProvider(feed.http, CLOCK, "en")
    result = await provider.collect(QUERY)
    await feed.http.aclose()
    assert len(result.items) == 1 and result.items[0].title == "Moskva issued"
