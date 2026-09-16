"""Research wiring regressions and revocation across the collection await boundary."""

import json
from collections.abc import Awaitable, Callable
from datetime import timedelta

import httpx
import pytest

from ase.adapters.feeds.google_news import SPEC as GOOGLE_SPEC
from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.api.schemas_reports import ReportCreateIn
from ase.container import Container
from ase.container.research import research_service
from ase.domain.errors import InvalidRequest
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchQuery,
)
from ase.domain.research_plan import ResearchPlan
from ase.domain.teams import MembershipRole
from ase.domain.users import User
from feeds_helpers import make_event
from helpers import USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, good_body
from research_records_helpers import CLOCK, RecordService
from team_helpers import CONTEXT, team_service

DIRECTION = json.dumps(
    {
        "pir": "What changed?",
        "sirs": ["Recent reporting"],
        "eeis": [],
        "search_terms": ["research"],
        "categories": ["news"],
    }
)
REGIONAL_IDS = tuple(seed.spec.id for seed in REGIONAL_SEEDS)


class CollectionProbe:
    def plan(self, query: ResearchQuery) -> ResearchPlan:
        return ResearchPlan(
            query.question, query.since, query.until, query.languages, (), 6, 45, 200
        )

    def __init__(self, callback: Callable[[], Awaitable[None]] | None = None) -> None:
        self.queries: list[ResearchQuery] = []
        self.callback = callback
        self.items = ()

    async def collect(self, query: ResearchQuery, *, replan=None) -> ResearchBatch:
        self.queries.append(query)
        if self.callback is not None:
            await self.callback()
        self.items = tuple(
            make_event(
                f"private-research-{index}",
                title=f"Research finding {index}",
                published_at=query.until - timedelta(hours=1),
                observed_at=query.until,
            )
            for index in range(3)
        )
        return ResearchBatch(
            items=self.items,
            attempts=(
                CollectionAttempt("fixture", "Owned fixture", CollectionStatus.COMPLETED, 3),
            ),
        )


async def prepare_models(client: httpx.AsyncClient, admin: User, container: Container) -> None:
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})


async def test_language_case_variants_make_one_guarded_edition_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = ReportCreateIn.model_validate(
        {
            "template": "ask",
            "question": "A private research question",
            "research_mode": "quick",
            "research_languages": ["zh-CN", "zh-cn"],
        }
    )
    query = ResearchQuery(
        body.question or "",
        CLOCK.now() - timedelta(days=1),
        CLOCK.now(),
        languages=body.to_request().research_languages,
        terms=("research",),
        source_ids=("research_google_news_zh-cn",),
    )
    response = httpx.Response(200, text="<rss><channel></channel></rss>")
    service = RecordService(monkeypatch, response=response)
    try:
        batch = await research_service(service.http, CLOCK, REGIONAL_IDS).collect(query)
        assert query.languages == ("zh-cn",)
        assert len(service.requests) == len(service.guarded) == 1
        assert service.requests[0].url.host == "news.google.com"
        assert service.requests[0].url.params["hl"] == "zh-CN"
        assert query.question not in str(service.requests[0].url)
        assert len(batch.attempts) == 1
        assert batch.attempts[0].source_id == "research_google_news_zh-cn"
        assert batch.attempts[0].status is CollectionStatus.EMPTY
    finally:
        await service.http.aclose()


@pytest.mark.parametrize("disabled_google", [GOOGLE_SPEC.id, "research_google_news_en"])
async def test_disabling_base_or_research_google_source_prevents_http(
    monkeypatch: pytest.MonkeyPatch,
    disabled_google: str,
) -> None:
    service = RecordService(monkeypatch, response=httpx.Response(500))
    query = ResearchQuery(
        "Private question",
        CLOCK.now() - timedelta(days=1),
        CLOCK.now(),
        terms=("research",),
        source_ids=("research_google_news_en",),
    )
    try:
        with pytest.raises(InvalidRequest, match="Selected sources are unavailable"):
            await research_service(service.http, CLOCK, (*REGIONAL_IDS, disabled_google)).collect(
                query
            )
        assert service.requests == service.guarded == []
    finally:
        await service.http.aclose()


@pytest.mark.parametrize("focus", ["company", "domain", "document", "media"])
async def test_record_research_with_country_is_rejected_before_collection(
    client: httpx.AsyncClient,
    container: Container,
    user: User,
    focus: str,
) -> None:
    probe = CollectionProbe()
    container.research = probe
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(
        "/api/reports",
        json={
            "template": "ask",
            "question": "Research the supplied subject",
            "research_mode": "quick",
            "research_focus": focus,
            "research_subject": "example.com",
            "country": "US",
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert "Country filters are unavailable for record-focused research" in response.text
    assert probe.queries == []
    # General research may still use a country, and ordinary report behaviour is retained.
    assert (
        ReportCreateIn.model_validate(
            {
                "template": "ask",
                "question": "Question",
                "country": "US",
                "research_mode": "quick",
                "research_focus": "general",
            }
        ).country
        == "US"
    )
    assert (
        ReportCreateIn.model_validate(
            {
                "template": "country_brief",
                "country": "US",
            }
        ).country
        == "US"
    )


@pytest.mark.parametrize("mode", ["quick", "detailed"])
async def test_research_plans_queries_for_non_question_template(
    client: httpx.AsyncClient,
    container: Container,
    admin: User,
    user: User,
    mode: str,
) -> None:
    await prepare_models(client, admin, container)
    probe = CollectionProbe()
    container.research = probe
    gateway = ScriptedGateway(DIRECTION, json.dumps(good_body()))
    container.llm = gateway
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(
        "/api/reports",
        json={
            "template": "intsum",
            "question": "What changed?",
            "research_mode": mode,
            "research_languages": ["fr"],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert probe.queries[0].terms == ("research",)
    assert probe.queries[0].languages == ("fr",)
    assert gateway.requests[0].schema_name == "direction"
    payload = response.json()["version"]
    assert payload["research"]["terms"] == ["research"]
    assert payload["research"]["mode"] == mode
    assert len(payload["evidence"]) == 3
    assert not any(finding["rule"] == "research_query_plan" for finding in payload["findings"])
    assert all(container.store.get(item.id) is None for item in probe.items)


async def test_membership_revoked_during_collection_blocks_report_and_usage(
    client: httpx.AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    async with team_service(container) as service:
        team = await service.create(admin, "Research team", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    await prepare_models(client, admin, container)
    revoked = False

    async def revoke_membership() -> None:
        nonlocal revoked
        async with team_service(container) as service:
            await service.remove_member(admin, team.id, user.id, CONTEXT)
        revoked = True

    probe = CollectionProbe(revoke_membership)
    container.research = probe
    container.llm = ScriptedGateway(DIRECTION, json.dumps(good_body()))
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(
        "/api/reports",
        json={
            "template": "ask",
            "question": "Private team research question",
            "research_mode": "quick",
            "team_id": str(team.id),
        },
        headers=headers,
    )
    assert revoked and len(probe.queries) == 1
    assert response.status_code == 404, response.text
    assert "Private team research" not in response.text
    assert "Research finding" not in response.text
    assert all(container.store.get(item.id) is None for item in probe.items)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        assert await repos.reports.list_recent(20) == []
        assert await repos.llm_usage.list_recent(20) == []
