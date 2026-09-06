"""Deterministic plans govern requests and preserve bounded, attributable query choices."""

import asyncio
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from ase.api.schemas_reports import ReportCreateIn
from ase.application.reports.request import ReportRequest
from ase.application.reports.research_export import research_sections
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import TEMPLATES
from ase.application.research.collection import CollectionBudget, ResearchCollector
from ase.application.research.service import ResearchCollectionService
from ase.domain.errors import InvalidRequest
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery
from ase.domain.research_plan import QueryVariant
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

NOW = datetime(2026, 9, 6, tzinfo=UTC)
QUERY = ResearchQuery("What changed?", NOW - timedelta(days=1), NOW, terms=("original",))


@dataclass
class Provider:
    id: str
    language: str = "en"
    name: str = "Fixture"
    queries: list[ResearchQuery] = field(default_factory=list)
    wait: bool = False

    def supports(self, query: ResearchQuery) -> bool:
        return True

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        self.queries.append(query)
        if self.wait:
            await asyncio.Event().wait()
        return ResearchBatch()


async def test_selection_and_variants_govern_actual_requests_and_frozen_receipt() -> None:
    english, persian = Provider("english"), Provider("persian", "fa")
    query = replace(
        QUERY,
        languages=("en", "fa"),
        source_ids=("persian",),
        query_variants=(QueryVariant("fa", ("شرکت نفت",)),),
    )
    result = await ResearchCollector([english, persian]).collect(query)
    assert english.queries == []
    assert persian.queries[0].terms == ("شرکت نفت",)
    assert result.plan is not None
    assert result.plan.tasks[1].provenance == "operator_supplied_variant"
    assert result.plan.tasks[0].selected is False
    assert result.plan.model_calls == result.plan.translation_calls == 0
    assert "complete historical coverage is not established" in result.plan.tasks[1].temporal_scope
    receipt = ResearchReceipt.build(query, result.attempts, 0, result.plan)
    exported = str(research_sections(receipt))
    assert "operator_supplied_variant" in exported and "شرکت نفت" in exported
    assert research_from_dict(research_to_dict(receipt)) == receipt
    old = research_to_dict(receipt)
    del old["plan"]
    assert research_from_dict(old).plan is None  # type: ignore[union-attr]


async def test_unknown_source_rejected_before_any_collection() -> None:
    provider = Provider("allowed")
    with pytest.raises(InvalidRequest):
        await ResearchCollector([provider]).collect(
            replace(QUERY, source_ids=("https://evil.test",))
        )
    assert provider.queries == []


async def test_empty_selection_makes_no_requests_and_default_keeps_existing_sources() -> None:
    provider = Provider("allowed")
    collector = ResearchCollector([provider])
    empty = await collector.collect(replace(QUERY, source_ids=()))
    assert empty.attempts == () and provider.queries == []
    await collector.collect(QUERY)
    assert len(provider.queries) == 1


async def test_actual_provider_temporal_metadata_matches_preview_and_frozen_run() -> None:
    class CurrentProvider(Provider):
        temporal_scope = "Current observation only; no historical reconstruction."

    provider = CurrentProvider("current")
    service = ResearchCollectionService(lambda query: [provider])
    preview = service.plan(QUERY)
    assert provider.queries == []
    collected = await service.collect(QUERY)
    assert collected.plan == preview
    assert preview.tasks[0].temporal_scope == provider.temporal_scope


async def test_explicit_source_language_alias_routes_identical_preview_and_run_terms() -> None:
    class ChineseProvider(Provider):
        query_language_aliases = ("zh-cn", "zh-hans")

    provider = ChineseProvider("regional", "zh")
    service = ResearchCollectionService(lambda query: [provider])
    query = replace(QUERY, languages=("zh-cn",), query_variants=(QueryVariant("zh-CN", ("证据",)),))
    preview = service.plan(query)
    result = await service.collect(query)
    assert result.plan == preview
    assert provider.queries[0].terms == ("证据",)
    assert preview.tasks[0].query_language == "zh-CN"
    ambiguous = replace(
        query,
        languages=("zh-cn", "zh-hans"),
        query_variants=(QueryVariant("zh-cn", ("one",)), QueryVariant("zh-hans", ("two",))),
    )
    with pytest.raises(InvalidRequest):
        service.plan(ambiguous)
    assert len(provider.queries) == 1
    traditional = replace(
        query, languages=("zh-tw",), query_variants=(QueryVariant("zh-tw", ("證據",)),)
    )
    assert service.plan(traditional).tasks[0].terms == QUERY.terms


async def test_selected_variants_share_existing_total_request_budget() -> None:
    providers = [Provider(str(index)) for index in range(8)]
    query = replace(QUERY, query_variants=(QueryVariant("en", ("operator",)),))
    result = await ResearchCollector(providers).collect(query)
    assert sum(len(provider.queries) for provider in providers) == 6
    assert result.plan is not None and result.plan.request_limit == 6
    assert result.plan.seconds_limit == 45 and result.plan.item_limit == 200
    assert result.attempts[-1].status is CollectionStatus.BUDGET_EXHAUSTED


async def test_selection_cancellation_stops_remaining_tasks() -> None:
    first, second = Provider("first", wait=True), Provider("second")
    task = asyncio.create_task(
        ResearchCollector([first, second]).collect(
            replace(QUERY, source_ids=("first", "second")), budget=CollectionBudget(2, 1, 1, 2)
        )
    )
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert second.queries == []


async def test_challenge_routing_keeps_selection_but_not_original_variant_terms() -> None:
    first, second = Provider("first"), Provider("second")
    service = ResearchCollectionService(lambda query: [first, second])
    query = replace(
        QUERY,
        source_ids=("second",),
        terms=("counterevidence",),
        query_variants=(QueryVariant("en", ("original operator variant",)),),
    )
    await service.challenge_many((query,))
    assert first.queries == [] and second.queries[0].terms == ("counterevidence",)


def test_request_scope_round_trip_preserves_operator_choices() -> None:
    body = ReportCreateIn(
        template="ask_the_eye",
        question="What changed?",
        research_mode="quick",
        research_source_ids=["source"],
        research_terms=["original"],
        research_query_variants=[{"language": "en", "terms": ["variant"]}],
    )
    request = body.to_request()
    scope = report_scope(request, next(iter(TEMPLATES.values())))
    restored = ReportRequest.from_scope(request.template_id, scope)
    assert restored.research_source_ids == request.research_source_ids
    assert restored.research_query_variants == request.research_query_variants
    assert restored.research_terms == request.research_terms


@pytest.mark.usefixtures("user")
async def test_preview_is_authenticated_and_returns_inventory_without_external_requests(
    client: AsyncClient,
) -> None:
    body = {
        "question": "What changed?",
        "since": QUERY.since.isoformat(),
        "until": NOW.isoformat(),
        "terms": ["bounded"],
    }
    assert (await client.post("/api/research/runs/plan", json=body)).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post("/api/research/runs/plan", json=body, headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["request_limit"] == 6
    assert response.json()["tasks"]
    invalid = await client.post(
        "/api/research/runs/plan", json={**body, "source_ids": ["unknown"]}, headers=bearer(token)
    )
    assert invalid.status_code == 422
