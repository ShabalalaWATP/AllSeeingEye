"""Persisted source controls guard live/private admission and administrator test results."""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from ase.adapters.persistence.source_controls import SqlSourceAdmission, SqlSourceControlRepository
from ase.application.research.source_admission import ControlledResearchProvider
from ase.container import Container
from ase.domain.research import CollectionStatus, ResearchBatch
from ase.domain.users import User
from feeds_helpers import FakeConnector, make_event
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_events_api import app  # noqa: F401 (shared isolated connector fixture)
from test_research_collection import QUERY, Provider, event


async def disable(container: Container, actor: User, source_id: str) -> None:
    async with container.session_factory() as session:
        await SqlSourceControlRepository(session).set(
            source_id, False, container.clock.now(), actor.id
        )
        await session.commit()


async def test_activation_persists_and_blocks_live_fetch(
    client: AsyncClient, container: Container, admin: User
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.patch(
        "/api/admin/sources/fake_feed/activation", headers=bearer(token), json={"enabled": False}
    )
    assert response.status_code == 204
    connector = container.connectors[0]
    assert isinstance(connector, FakeConnector)
    outcome = await container.scheduler.poll_once(connector)
    assert not outcome.ok and connector.calls == 0
    assert container.store.stats().total == 0
    assert not await SqlSourceAdmission(container.session_factory).enabled("fake_feed")
    listed = await client.get("/api/admin/sources", headers=bearer(token))
    item = next(item for item in listed.json()["items"] if item["id"] == "fake_feed")
    assert item["enabled"] is False and item["test_available"] is True
    response = await client.patch(
        "/api/admin/sources/fake_feed/activation", headers=bearer(token), json={"enabled": True}
    )
    assert response.status_code == 204
    assert (await container.scheduler.poll_once(connector)).ok
    assert connector.calls == 1


async def test_disabled_during_live_fetch_does_not_publish(
    container: Container, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    connector = container.connectors[0]

    async def fetched():
        await disable(container, admin, connector.spec.id)
        return [make_event()]

    monkeypatch.setattr(connector, "fetch", fetched)
    result = await container.scheduler.poll_once(connector)
    assert not result.ok
    assert container.store.stats().total == 0
    assert container.health.get(connector.spec.id).polls == 0


@pytest.mark.parametrize("prefix", ["research_regional_", "research_publisher_"])
async def test_private_parent_admission_before_and_after_fetch(
    container: Container, admin: User, prefix: str
) -> None:
    gate = SqlSourceAdmission(container.session_factory)
    provider = Provider(f"{prefix}parent", ResearchBatch(items=(event("private"),)))
    await disable(container, admin, "parent")
    result = await ControlledResearchProvider(provider, gate).collect(QUERY)
    assert provider.called == 0
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE
    fresh = Provider(f"{prefix}regional", ResearchBatch(items=(event("private"),)))
    original = fresh.collect

    async def collect(query):
        batch = await original(query)
        await disable(container, admin, "regional")
        return batch

    fresh.collect = collect
    result = await ControlledResearchProvider(fresh, gate).collect(QUERY)
    assert fresh.called == 1 and result.items == ()
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert container.store.stats().total == 0
    await disable(container, admin, "google_news")
    assert not await gate.enabled("research_google_news_fa")
    assert not await SqlSourceAdmission(container.session_factory, ("environment",)).enabled(
        "environment"
    )


async def test_admin_test_is_isolated_and_errors_are_safe(
    client: AsyncClient, container: Container, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    await disable(container, admin, "fake_feed")
    response = await client.post("/api/admin/sources/fake_feed/test", headers=bearer(token))
    assert response.status_code == 200 and response.json()["ok"] is True
    assert response.json()["fetched"] == 1
    assert container.store.stats().total == 0
    assert container.health.get("fake_feed").polls == 0
    monkeypatch.setattr(
        container.connectors[0],
        "fetch",
        AsyncMock(side_effect=RuntimeError("private-credential-value")),
    )
    failed = await client.post("/api/admin/sources/fake_feed/test", headers=bearer(token))
    assert failed.status_code == 200 and failed.json()["ok"] is False
    assert "private-credential-value" not in failed.text


async def test_test_release_rechecks_original_session(
    client: AsyncClient, container: Container, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)

    async def fetched():
        async with container.session_factory() as session:
            repos = container.repositories(session)
            await repos.refresh_tokens.revoke_family(
                container.issuer.verify(token).family_id, container.clock.now()
            )
            await repos.uow.commit()
        return [make_event()]

    monkeypatch.setattr(container.connectors[0], "fetch", fetched)
    response = await client.post("/api/admin/sources/fake_feed/test", headers=bearer(token))
    assert response.status_code == 401
    assert container.store.stats().total == 0


async def test_controls_require_admin_and_known_source(
    client: AsyncClient, admin: User, user: User
) -> None:
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    for route in ("test", "reset"):
        assert (
            await client.post(f"/api/admin/sources/fake_feed/{route}", headers=bearer(user_token))
        ).status_code == 403
    assert (
        await client.patch(
            "/api/admin/sources/fake_feed/activation",
            headers=bearer(user_token),
            json={"enabled": False},
        )
    ).status_code == 403
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert (
        await client.patch(
            "/api/admin/sources/unknown/activation", headers=bearer(token), json={"enabled": False}
        )
    ).status_code == 404
    listing = (await client.get("/api/admin/sources", headers=bearer(token))).json()["items"]
    research = next(item for item in listing if not item["test_available"])
    assert (
        await client.post(f"/api/admin/sources/{research['id']}/test", headers=bearer(token))
    ).status_code == 422


async def test_source_tests_cap_counts_timeout_and_rate_limit(
    client: AsyncClient,
    container: Container,
    admin: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    fetch = AsyncMock(return_value=[make_event()] * 1001)
    monkeypatch.setattr(container.connectors[0], "fetch", fetch)
    response = await client.post("/api/admin/sources/fake_feed/test", headers=bearer(token))
    assert response.json()["fetched"] == 1000 and response.json()["capped"] is True
    fetch.side_effect = TimeoutError()
    response = await client.post("/api/admin/sources/fake_feed/test", headers=bearer(token))
    assert response.json()["ok"] is False and "20-second" in response.json()["message"]
    await client.post("/api/admin/sources/fake_feed/test", headers=bearer(token))
    limited = await client.post("/api/admin/sources/fake_feed/test", headers=bearer(token))
    assert limited.status_code == 429 and fetch.call_count == 3


async def test_variant_activation_rejects_a_disabled_parent(
    client: AsyncClient,
    container: Container,
    admin: User,
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    await disable(container, admin, "google_news")
    response = await client.patch(
        "/api/admin/sources/research_google_news_en/activation",
        headers=bearer(token),
        json={"enabled": True},
    )
    assert response.status_code == 422
    assert "parent source" in response.text
