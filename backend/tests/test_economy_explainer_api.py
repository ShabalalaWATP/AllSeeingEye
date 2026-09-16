"""The explainer endpoints: private, honest when empty, and refreshable by admins only."""

from __future__ import annotations

from sqlalchemy import select

from ase.adapters.persistence.models import AuditLogRow
from economy_explainer_helpers import explainer_profile, install
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_economy_explainer import ScriptedGateway


async def audit_actions(container):
    async with container.session_factory() as session:
        rows = await session.scalars(select(AuditLogRow))
        return [(row.action, row.details) for row in rows]


async def test_the_explainer_needs_a_session_and_is_never_cached_by_the_browser(
    client, container, user, monkeypatch
):
    install(container, monkeypatch)
    container.llm = ScriptedGateway()
    assert (await client.get("/api/economy/explainer")).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    result = await client.get("/api/economy/explainer", headers=bearer(token))
    assert result.status_code == 200
    assert result.headers["cache-control"] == "private, no-store"


async def test_no_model_returns_an_honest_empty_state_rather_than_an_error(
    client, container, user, monkeypatch
):
    install(container, monkeypatch)
    container.llm = ScriptedGateway()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    body = (await client.get("/api/economy/explainer", headers=bearer(token))).json()
    assert body["status"] == "unavailable"
    assert body["explainer"] is None and body["provenance"] is None
    assert "No model is available" in body["reason"]


async def test_a_signed_in_reader_triggers_one_generation_and_sees_its_provenance(
    client, container, user, monkeypatch
):
    install(container, monkeypatch)
    await explainer_profile(container)
    gateway = ScriptedGateway()
    container.llm = gateway
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    body = (await client.get("/api/economy/explainer", headers=bearer(token))).json()
    assert body["status"] == "ready" and body["stale"] is False
    assert body["provenance"]["model"] == "economy-fixture-model"
    assert body["provenance"]["sources"][0] == "World Bank annual indicators"
    assert "source of truth" in body["provenance"]["written_by"]
    assert len(body["explainer"]["regions"]) == 5
    assert body["explainer"]["regions"][0]["id"] == "GB"
    assert len(body["explainer"]["world"]["paragraphs"]) == 2
    assert body["explainer"]["glossary"][0]["term"] == "Inflation"
    # A second reader is served the same stored text without another model call.
    (await client.get("/api/economy/explainer", headers=bearer(token))).json()
    assert len(gateway.requests) == 1


async def test_only_administrators_may_force_a_refresh(client, container, user, monkeypatch):
    install(container, monkeypatch)
    await explainer_profile(container)
    container.llm = ScriptedGateway()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    refused = await client.post("/api/economy/explainer/refresh", headers=bearer(token))
    assert refused.status_code == 403
    entries = [entry for entry in await audit_actions(container) if entry[0].startswith("economy")]
    assert entries == []


async def test_an_administrator_refresh_is_audited(client, container, admin, monkeypatch):
    install(container, monkeypatch)
    await explainer_profile(container)
    gateway = ScriptedGateway()
    container.llm = gateway
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    result = await client.post("/api/economy/explainer/refresh", headers=bearer(token))
    assert result.status_code == 200 and result.json()["status"] == "ready"
    assert result.headers["cache-control"] == "private, no-store"
    entries = [entry for entry in await audit_actions(container) if entry[0].startswith("economy")]
    assert entries == [("economy_explainer_refreshed", {"status": "ready", "stale": False})]
    assert len(gateway.requests) == 1


async def test_a_refresh_that_fails_its_checks_is_still_audited_and_reported(
    client, container, admin, monkeypatch
):
    install(container, monkeypatch)
    await explainer_profile(container)
    container.llm = ScriptedGateway('{"world": {}}', '{"world": {}}')
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    body = (await client.post("/api/economy/explainer/refresh", headers=bearer(token))).json()
    assert body["status"] == "validation_failed" and body["explainer"] is None
    entries = [entry for entry in await audit_actions(container) if entry[0].startswith("economy")]
    assert entries == [
        ("economy_explainer_refreshed", {"status": "validation_failed", "stale": False})
    ]
