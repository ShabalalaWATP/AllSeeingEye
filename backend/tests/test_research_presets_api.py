"""Preset HTTP access preserves current sessions, source controls and saved-brief boundaries."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from ase.api.session_fence import SessionFence
from ase.container import Container
from ase.domain.errors import Unauthenticated
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from test_source_controls import disable


async def test_authenticated_search_and_readiness_are_safe_and_uncached(
    client: AsyncClient,
    user: User,
    app: FastAPI,
) -> None:
    assert "/api/research/presets" in app.openapi()["paths"]
    endpoint = "/api/research/presets"
    assert (await client.get(endpoint)).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get(endpoint, headers=bearer(token))
    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "private, no-store"
    assert len(response.json()["items"]) == 20
    assert "actor_perspective" in response.json()["lens_choices"]
    found = await client.get(endpoint + "?q=Iran&group=economy", headers=bearer(token))
    assert [row["preset"]["id"] for row in found.json()["items"]] == ["economy-iran"]
    assert (await client.get(endpoint + "?q=absent-topic", headers=bearer(token))).json()[
        "items"
    ] == []
    assert (await client.get(endpoint + "?group=private", headers=bearer(token))).status_code == 422
    assert (
        await client.get(endpoint + "?q=" + "x" * 121, headers=bearer(token))
    ).status_code == 422
    assert "source_sha256" not in response.text
    assert "api_key_value" not in response.text


async def test_definition_is_editable_pinned_and_basic_reduction_is_explicit(
    client: AsyncClient,
    user: User,
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    endpoint = "/api/research/presets/conflict-global/definition"
    assert (await client.post(endpoint, json={"version": 1})).status_code == 401
    response = await client.post(endpoint, headers=headers, json={"version": 1})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["definition"]["preset_id"] == "conflict-global"
    assert result["definition"]["preset_version"] == 1
    assert result["definition"]["team_id"] is None
    assert "identity" not in result["definition"]
    assert not (await client.get("/api/research/briefs", headers=headers)).json()["items"]
    selected = [result["definition"]["question"]["requirements"][0]["id"]]
    assert (
        await client.post(endpoint, headers=headers, json={"version": 1, "depth": "quick"})
    ).status_code == 422
    reduced = await client.post(
        endpoint,
        headers=headers,
        json={
            "version": 1,
            "depth": "quick",
            "lens": "actor_perspective",
            "selected_requirement_ids": selected,
        },
    )
    assert reduced.status_code == 200, reduced.text
    assert len(reduced.json()["omitted_requirement_ids"]) == 3
    assert reduced.json()["definition"]["lens"]["id"] == "actor_perspective"
    assert (await client.post(endpoint, headers=headers, json={"version": 99})).status_code == 409
    assert (
        await client.post(
            "/api/research/presets/unknown/definition", headers=headers, json={"version": 1}
        )
    ).status_code == 404
    assert (
        await client.post(endpoint, headers=headers, json={"version": 1, "owner_id": "forged"})
    ).status_code == 422
    failed = await client.post(
        endpoint,
        headers=headers,
        json={
            "version": 1,
            "selected_source_ids": ["private-sentinel-source"],
        },
    )
    assert failed.status_code == 422 and "private-sentinel-source" not in failed.text


async def test_saved_copy_preserves_owner_version_and_other_users_cannot_read_it(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    result = await client.post(
        "/api/research/presets/economy-uk/definition",
        headers=headers,
        json={"version": 1, "lens": "uk_policy"},
    )
    definition = result.json()["definition"]
    definition["title"] = "Private edited UK brief"
    definition["question"]["main"] = "PRIVATE_PRESET_COPY_SENTINEL"
    saved = await client.post("/api/research/briefs", headers=headers, json=definition)
    assert saved.status_code == 201, saved.text
    brief = saved.json()["brief"]
    assert brief["identity"]["owner_id"] == str(user.id)
    assert brief["identity"]["preset_version"] == 1
    assert brief["lens"]["id"] == "uk_policy"
    other = await create_user(
        container, email="preset-other@example.com", password="another-long-passphrase"
    )
    other_token = await login_token(client, other.email, "another-long-passphrase")
    response = await client.get(
        "/api/research/briefs/" + brief["identity"]["id"], headers=bearer(other_token)
    )
    assert response.status_code == 404
    catalogue = await client.get("/api/research/presets", headers=bearer(other_token))
    assert "PRIVATE_PRESET_COPY_SENTINEL" not in catalogue.text


async def test_disabled_sources_stay_visible_but_cannot_enter_definition(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await disable(container, admin, "google_news")
    endpoint = "/api/research/presets/cyber-global/definition"
    response = await client.post(endpoint, headers=bearer(token), json={"version": 1})
    assert response.status_code == 200, response.text
    data = response.json()
    sources = data["readiness"]["sources"]
    google = [row for row in sources if row["id"].startswith("research_google_news_")]
    assert google and all(row["readiness"] == "disabled" for row in google)
    assert all(
        not key.startswith("research_google_news_")
        for key in data["definition"]["collection"]["source_ids"]
    )
    assert any(row["id"] == "gap.network_telemetry" for row in data["readiness"]["gaps"])


@pytest.mark.parametrize("definition", [False, True])
async def test_session_revalidated_before_catalogue_or_definition_release(
    client: AsyncClient,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    definition: bool,
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    check = AsyncMock(side_effect=Unauthenticated("Session ended"))
    monkeypatch.setattr(SessionFence, "confirm", check)
    if definition:
        response = await client.post(
            "/api/research/presets/economy-uk/definition",
            headers=bearer(token),
            json={"version": 1},
        )
    else:
        response = await client.get("/api/research/presets", headers=bearer(token))
    assert response.status_code == 401
    check.assert_awaited_once()
