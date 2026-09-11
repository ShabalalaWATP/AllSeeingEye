"""Country scopes remain bounded and exclude unrelated retained evidence."""

from dataclasses import replace
from datetime import timedelta

import httpx
import pytest
from pydantic import ValidationError

from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.adapters.research.regional import RegionalFeedResearchProvider
from ase.adapters.research_records.ooni import OoniAggregateProvider
from ase.adapters.store.memory import InMemoryEventStore
from ase.api.schemas_reports import ReportCreateIn
from ase.api.schemas_research_plan import ResearchPlanIn
from ase.application.ports.feeds import EventQuery
from ase.application.reports.request import ReportRequest
from ase.application.reports.research import collect_report_evidence
from ase.application.reports.scope import report_scope
from ase.application.reports.selection import MAX_POOL, select_evidence
from ase.application.reports.templates import template_for
from ase.application.research.planning import build_plan
from ase.application.research.service import ResearchCollectionService
from ase.domain.research import ResearchMode
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from ase.domain.research_scope import normalise_countries
from research_feed_helpers import CLOCK, PublicFeed
from test_research_collection import NOW, QUERY, Provider, event


@pytest.mark.parametrize(
    ("legacy", "countries", "expected"),
    [
        (None, (), ()),
        ("gb", (), ("GB",)),
        (None, ["ua", "PL", "ua"], ("UA", "PL")),
        ("gb", ["GB", "gb"], ("GB",)),
    ],
)
def test_canonical_countries_preserve_legacy_and_deduplicate(legacy, countries, expected):
    assert normalise_countries(legacy, countries) == expected


@pytest.mark.parametrize("countries", [None, "GB", {}, ["ZZ"], [1], [None], [" GB"], ["GB"] * 9])
def test_malformed_country_list_never_becomes_worldwide(countries):
    with pytest.raises(ValueError):
        normalise_countries(None, countries)
    with pytest.raises(ValueError):
        ReportRequest.from_scope("ask", {"countries": countries})


def test_conflicting_legacy_scope_is_rejected_by_both_entry_points():
    with pytest.raises(ValueError, match="legacy country"):
        normalise_countries(123, ())
    with pytest.raises(ValidationError):
        ReportCreateIn(template="ask", country="GB", countries=["GB", "UA"])
    with pytest.raises(ValidationError):
        ResearchPlanIn(
            question="Question",
            since=QUERY.since,
            until=QUERY.until,
            country_iso="GB",
            countries=["UA"],
        )


def test_report_and_plan_scope_survive_frozen_round_trip():
    request = ReportCreateIn(
        template="ask",
        question="Compare railway disruptions",
        countries=["ua", "PL"],
        research_mode="quick",
        research_web_search=True,
        research_since=NOW - timedelta(days=500),
        research_until=NOW,
    ).to_request()
    assert request.country_isos == ("UA", "PL") and request.country_iso is None
    frozen = report_scope(request, template_for("ask"))
    assert ReportRequest.from_scope("ask", frozen) == request
    query = replace(
        QUERY,
        country_isos=request.country_isos,
        research_web_search=True,
        since=request.research_since,
        until=request.research_until,
    )
    plan = build_plan(query, [], requests=6, seconds=45, items=200)
    receipt = ResearchReceipt.build(query, (), 0, plan)
    restored = research_from_dict(research_to_dict(receipt))
    assert restored == receipt
    assert restored.plan.country_isos == ("UA", "PL")
    assert restored.plan.research_web_search is True
    malformed = research_to_dict(receipt)
    malformed["plan"]["country_isos"] = "UA"
    with pytest.raises(ValueError):
        research_from_dict(malformed)


def test_legacy_single_country_frozen_plan_encoding_stays_compatible():
    query = replace(QUERY, country_iso="GB")
    plan = build_plan(query, [], requests=6, seconds=45, items=200)
    frozen = research_to_dict(ResearchReceipt.build(query, (), 0, plan))
    assert frozen["plan"]["country_iso"] == "GB"
    assert "country_isos" not in frozen["plan"]
    assert "research_web_search" not in frozen["plan"]
    assert research_to_dict(research_from_dict(frozen)) == frozen


class RecordingStore(InMemoryEventStore):
    def __init__(self):
        super().__init__()
        self.queries = []

    def query(self, query):
        self.queries.append(query)
        return super().query(query)


def populated_store():
    store = RecordingStore()
    store.upsert(
        [event(iso).with_changes(country_iso=iso, source_id=iso) for iso in ("UA", "PL", "US")]
    )
    store.upsert([event("unknown"), event("too-late", NOW).with_changes(country_iso="UA")])
    return store


def test_multi_country_selection_never_queries_worldwide_and_excludes_other_nations():
    store = populated_store()
    result = select_evidence(
        store,
        {},
        template_for("ask").strategy,
        now=NOW,
        countries=("UA", "PL"),
        until=NOW,
    )
    assert {row.title for row in result.items} == {"UA", "PL"}
    assert [query.country_iso for query in store.queries] == ["UA", "PL"]
    assert sum(query.limit for query in store.queries) <= MAX_POOL


async def test_retained_seed_is_strictly_scoped_and_uses_one_shared_limit():
    store = populated_store()
    query = replace(QUERY, country_isos=("UA", "PL"))
    request = ReportRequest("ask", country_isos=("UA", "PL"), research_mode=ResearchMode.QUICK)
    private, _ = await collect_report_evidence(
        query,
        request,
        ResearchCollectionService(lambda _: []),
        InMemoryEventStore,
        store,
    )
    assert {row.id for row in private.query(EventQuery(limit=20))} == {"UA", "PL"}
    assert [query.country_iso for query in store.queries] == ["UA", "PL"]
    assert sum(query.limit for query in store.queries) <= 1000
    assert store.stats().total == 5


async def test_country_membership_routes_regional_sources_without_hidden_fanout(monkeypatch):
    feed = PublicFeed(monkeypatch, httpx.Response(200, text="unused"))
    seed = next(seed for seed in REGIONAL_SEEDS if seed.spec.id == "meduza_ru")
    provider = RegionalFeedResearchProvider(feed.http, CLOCK, seed)
    query = replace(QUERY, terms=("railway",), languages=("ru",), country_isos=("UA", "RU"))
    assert provider.supports(query)
    assert not provider.supports(replace(query, country_isos=("UA", "PL")))
    # This connector needs a single-country API request. A plural scope is visible as unsupported.
    ooni = OoniAggregateProvider(feed.http, CLOCK)
    query = replace(query, subject="ooni:UA", source_ids=(ooni.id,))
    result = await ooni.collect(query)
    assert result.attempts[0].status.value == "unsupported"
    assert not feed.requests
    await feed.http.aclose()


async def test_replan_cannot_expand_country_scope():
    providers = [Provider(str(i)) for i in range(3)]
    query = replace(QUERY, country_isos=("UA", "PL"))

    async def change_scope(original, first, remaining):
        return replace(original, country_isos=(), terms=("changed",))

    result = await ResearchCollectionService(lambda _: providers).collect(
        query, replan=change_scope
    )
    assert result.plan.country_isos == ("UA", "PL")
    assert all(row.plan.country_isos == ("UA", "PL") for row in result.passes)
