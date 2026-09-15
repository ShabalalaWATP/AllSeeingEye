"""Saved-revision preview HTTP boundaries and proof that preview does not dispatch work."""

from copy import deepcopy
from dataclasses import replace

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from ase.adapters.feeds.http import FeedHttpClient
from ase.api.routers.research_preflight import router
from ase.application.access import AccessPolicy
from ase.application.model_routing import ModelRouting
from ase.container import Container
from ase.domain.teams import MembershipRole
from ase.domain.users import User
from helpers import ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from team_helpers import CONTEXT, team_service
from test_research_brief_api import _draft


@pytest.fixture(autouse=True)
def install_preflight(app: FastAPI) -> None:
    path = "/api/research/briefs/{brief_id}/revisions/{revision}/preflight"
    if path not in app.openapi()["paths"]:
        app.include_router(router, prefix="/api")
        app.openapi_schema = None


async def test_exact_revision_no_expenditure_and_private_response(
    client: AsyncClient, user: User, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    draft = _draft()
    draft["observation"].update(policy="relative", lookback_hours=48, forecast_horizon_days=30)
    saved = await client.post("/api/research/briefs", json=draft, headers=bearer(token))
    assert saved.status_code == 201, saved.text
    identity = saved.json()["brief"]["identity"]
    base = f"/api/research/briefs/{identity['id']}/revisions"
    edited = deepcopy(draft)
    edited.update(base_revision=1, title="Newer question")
    assert (await client.post(base, json=edited, headers=bearer(token))).status_code == 201

    async def forbidden(*args, **kwargs):
        pytest.fail("Preflight dispatched source or model work")

    monkeypatch.setattr(FeedHttpClient, "get_bytes", forbidden)
    monkeypatch.setattr(FeedHttpClient, "get_secret_bytes", forbidden)
    monkeypatch.setattr(ModelRouting, "snapshot", forbidden)
    assert (await client.get(base + "/1/preflight")).status_code == 401
    response = await client.get(base + "/1/preflight", headers=bearer(token))
    assert response.status_code == 200, response.text
    preview = response.json()["preflight"]
    assert preview["revision"] == 1 and preview["title"] == draft["title"]
    assert preview["forecast_horizon_days"] == 30
    assert preview["until"] == preview["as_of"]
    assert preview["preview_only"] and not preview["admission_checked"]
    assert preview["model_calls"] == preview["provider_calls"] == 0
    assert response.headers["Cache-Control"] == "private, no-store"
    assert (await client.get(base + "/2/preflight", headers=bearer(token))).json()["preflight"][
        "title"
    ] == "Newer question"
    assert (await client.get(base + "/99/preflight", headers=bearer(token))).status_code == 404
    assert (await client.get(base + "/0/preflight", headers=bearer(token))).status_code == 422
    assert (await client.post(base + "/1/preflight", headers=bearer(token))).status_code == 405


async def test_personal_brief_is_hidden_from_another_user(
    client: AsyncClient, container: Container, user: User
) -> None:
    stranger = await create_user(
        container, email="preview-stranger@example.com", password="another-long-passphrase"
    )
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    other = await login_token(client, stranger.email, "another-long-passphrase")
    saved = await client.post("/api/research/briefs", json=_draft(), headers=bearer(token))
    identity = saved.json()["brief"]["identity"]
    path = f"/api/research/briefs/{identity['id']}/revisions/1/preflight"
    response = await client.get(path, headers=bearer(other))
    assert response.status_code == 404
    assert "Regional developments" not in response.text


async def test_team_access_is_rechecked_before_release(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = await create_user(
        container, email="preview-reader@example.com", password="another-long-passphrase"
    )
    async with team_service(container) as service:
        team = await service.create(admin, "Preview desk", CONTEXT)
        for actor in (user, reader):
            await service.set_member(
                admin, team.id, email=actor.email, role=MembershipRole.MEMBER, context=CONTEXT
            )
    owner_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    reader_token = await login_token(client, reader.email, "another-long-passphrase")
    admin_token = await login_token(client, admin.email, ADMIN_PASSWORD)
    saved = await client.post(
        "/api/research/briefs",
        json={**_draft(), "team_id": str(team.id)},
        headers=bearer(owner_token),
    )
    identity = saved.json()["brief"]["identity"]
    path = f"/api/research/briefs/{identity['id']}/revisions/1/preflight"
    assert (await client.get(path, headers=bearer(reader_token))).status_code == 200
    assert (await client.get(path, headers=bearer(admin_token))).status_code == 200
    original = AccessPolicy.context
    checks = 0

    async def revoked_on_release(self, actor, *, for_update=False):
        nonlocal checks
        context = await original(self, actor, for_update=for_update)
        if actor.id == reader.id:
            checks += 1
            if checks >= 2:
                return replace(context, memberships={})
        return context

    monkeypatch.setattr(AccessPolicy, "context", revoked_on_release)
    result = await client.get(path, headers=bearer(reader_token))
    assert result.status_code == 404
    assert checks == 2


async def test_invalid_saved_template_has_safe_field_error(client: AsyncClient, user: User) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    draft = _draft()
    draft["output"]["template_id"] = "invalid-template"
    saved = await client.post("/api/research/briefs", json=draft, headers=bearer(token))
    assert saved.status_code == 201, saved.text
    identity = saved.json()["brief"]["identity"]
    result = await client.get(
        f"/api/research/briefs/{identity['id']}/revisions/1/preflight", headers=bearer(token)
    )
    assert result.status_code == 422
    assert "output.template_id" in result.json()["error"]["fields"]
