"""Real routing, durable frozen context and authentication with network-free providers."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.application.economy_briefing import economy_briefing_request
from ase.domain.economy import EconomyPoint, EconomySeries, EconomySnapshot
from ase.domain.economy_catalogue import INDICATORS, REGIONS
from ase.domain.events import Category
from ase.domain.research import ResearchBatch, ResearchFocus, ResearchMode, ResearchQuery
from ase.domain.research_capacity import MAX_COLLECTION_PROVIDERS
from feeds_helpers import make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_job_api_helpers import job_settings, prepared, stored, work
from test_economy_data import parse_world_bank, wb_payload, wb_row

__all__ = ["job_settings"]


def macro_fixture(now):
    return EconomySnapshot(
        now,
        now + timedelta(hours=1),
        parse_world_bank(
            wb_payload(
                *(
                    wb_row(countryiso3code=code, indicator={"id": indicator}, date="2024")
                    for _, _, code in REGIONS
                    for _, _, indicator, _ in INDICATORS
                )
            ),
            now,
        ),
        tuple(
            EconomySeries(
                code,
                f"{code} per EUR",
                "currency per euro",
                "daily",
                "ECB",
                "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml",
                "available",
                "Reference rate, not a transaction price.",
                now,
                (EconomyPoint("2026-08-31", value),),
            )
            for code, value in (("GBP", 0.8), ("USD", 1.1), ("CNY", 7.2))
        ),
    )


async def test_economy_news_authentication_scope_and_bounded_query(client, user, container):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    denied = await client.get("/api/economy/news")
    assert denied.status_code == 401
    at = container.clock.now() - timedelta(minutes=1)
    economic = make_event(
        "economic-article",
        source_id="economic_scmp_china",
        category=Category.ECONOMIC,
        title="Exports increased",
        published_at=at,
        observed_at=at,
        point=None,
    )
    container.store.upsert((economic, make_event("unrelated-conflict", category=Category.CONFLICT)))
    response = await client.get("/api/economy/news?region=CN", headers=headers)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["items"][0]["id"] == economic.id
    assert response.json()["items"][0]["region_codes"] == ["CN"]
    assert len(response.json()["items"]) == 1
    assert (await client.get("/api/economy/news?region=GB", headers=headers)).json()["items"] == []
    assert (await client.get("/api/economy/news?limit=101", headers=headers)).status_code == 422
    assert (await client.get("/api/economy/news?region=ZZ", headers=headers)).status_code == 422


async def test_news_disabled_between_preparation_and_release_is_removed(
    client,
    user,
    container,
    monkeypatch,
):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    at = container.clock.now() - timedelta(minutes=1)
    container.store.upsert(
        (
            make_event(
                "headline",
                source_id="economic_bbc_business",
                category=Category.ECONOMIC,
                title="Inflation latest",
                published_at=at,
                observed_at=at,
            ),
        )
    )
    original = container.economy_news.read

    async def disable_after_read(*args):
        result = await original(*args)
        assert result.items
        async with container.source_admission.guard(), container.session_factory() as session:
            await SqlSourceControlRepository(session).set(
                "economic_bbc_business",
                False,
                container.clock.now(),
                user.id,
            )
            await session.commit()
        return result

    monkeypatch.setattr(container.economy_news, "read", disable_after_read)
    response = await client.get("/api/economy/news", headers=headers)
    assert response.status_code == 200 and response.json()["items"] == []


def test_expanded_inventory_keeps_economic_selection_and_multilingual_company_plans(container):
    request = economy_briefing_request()
    query = ResearchQuery(
        question=request.question,
        since=container.clock.now() - timedelta(hours=24),
        until=container.clock.now(),
        terms=request.research_terms,
        source_ids=request.research_source_ids,
        mode=ResearchMode.DETAILED,
    )
    plan = container.research.plan(query)
    assert {row.source_id for row in plan.tasks if row.selected} == set(request.research_source_ids)
    assert all(row.supported for row in plan.tasks if row.selected)
    company = container.research.plan(
        ResearchQuery(
            question="Company filing review",
            since=query.since,
            until=query.until,
            languages=("en", "ru", "zh", "fa", "fr", "de", "es", "ar"),
            terms=("company",),
            focus=ResearchFocus.COMPANY,
            subject="0000320193",
        )
    )
    # The enforced bound is the collection provider cap; the plan must stay inside it
    # as publisher inventories grow, or planning would refuse company questions.
    assert len(company.tasks) <= MAX_COLLECTION_PROVIDERS
    assert any(row.source_id == "research-sec-submissions" for row in company.tasks)


@pytest.mark.parametrize("days", [2, 14])
async def test_economic_briefing_freezes_dated_context_and_collects_financial_news_in_period(
    client,
    user,
    container,
    monkeypatch,
    days,
):
    gateway, headers = await prepared(container, client)
    # A deployment-disabled publisher is absent from the research catalogue.
    # Automatic briefing admission must keep using the remaining providers.
    unavailable_source = "research_publisher_economic_hm_treasury"
    container.research_sources = tuple(
        spec for spec in container.research_sources if spec.id != unavailable_source
    )
    snapshot = AsyncMock(return_value=macro_fixture(container.clock.now()))
    monkeypatch.setattr(container.economy, "snapshot", snapshot)
    assert (await client.post("/api/economy/briefing")).status_code == 401
    assert (await client.get("/api/economy/briefing", headers=headers)).status_code == 405
    response = await client.post(f"/api/economy/briefing?days={days}", headers=headers)
    assert response.status_code == 202, response.text
    job_id = response.json()["job"]["id"]
    assert response.json()["job"]["title"] == f"{days} day economic summary"
    assert not gateway.calls
    frozen = (await stored(container, job_id)).payload["input"]
    assert len(frozen["evidence"]) == 9
    assert all(
        "2024=" in item["summary"] and "not the observation date" in item["summary"]
        for item in frozen["evidence"]
        if item["source_id"] == "research-world-bank"
    )
    assert sum(item["source_id"] == "research-world-bank" for item in frozen["evidence"]) == 6
    assert all(item["published_at"] is None for item in frozen["evidence"])
    for item in frozen["evidence"]:
        if item["source_id"] == "research-world-bank":
            assert all(label in item["summary"] for _, label, _, _ in INDICATORS)
    again = await client.post(f"/api/economy/briefing?days={days}", headers=headers)
    assert again.json()["job"]["id"] == job_id and snapshot.await_count == 1
    at = container.clock.now() - timedelta(minutes=1)
    collect = AsyncMock(
        return_value=ResearchBatch(
            items=(
                make_event(
                    "financial",
                    source_id="economic_bbc_business",
                    category=Category.ECONOMIC,
                    title="Global inflation rises",
                    published_at=at,
                    observed_at=at,
                    point=None,
                ),
                *(
                    make_event(
                        f"financial-{age}-days",
                        source_id="economic_bbc_business",
                        category=Category.ECONOMIC,
                        title=f"Policy rate decision {age} days earlier",
                        published_at=container.clock.now() - timedelta(days=age),
                        observed_at=at,
                        point=None,
                    )
                    for age in (10, 15)
                ),
            )
        )
    )
    monkeypatch.setattr(container.research, "collect", collect)
    # Durable research jobs acquire sources through the checkpointed path.
    monkeypatch.setattr(container.research, "collect_checkpointed", collect)
    await work(container)
    current = await stored(container, job_id)
    assert current.status in {"completed", "needs_review"}, (current.status, current.error)
    async with container.session_factory() as session:
        version = await container.repositories(session).reports.get_version(current.report_id, 1)
    assert len(version.evidence) == (11 if days == 14 else 10)
    assert {row.source_id for row in version.evidence} == {
        "research-world-bank",
        "economic_bbc_business",
        "economic-ecb",
    }
    assert version.body.cited_labels() <= {row.label for row in version.evidence}
    model_context = " ".join(
        message.content for _, request in gateway.calls for message in request.messages
    )
    assert "Manufacturing value added: 2024=" in model_context
    assert "Debt covers central government only" in model_context
    assert f"{days} day economic summary" in model_context
    assert collect.call_args.args[0].since == container.clock.now() - timedelta(days=days)
    assert collect.call_args.args[0].until == container.clock.now()
    assert collect.call_args.args[0].source_ids == tuple(
        key for key in economy_briefing_request().research_source_ids if key != unavailable_source
    )
