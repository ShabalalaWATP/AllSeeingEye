"""Unsaved model discovery never persists keys or reuses them across endpoints."""

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.application.admin import llm_discovery
from ase.container import Container
from ase.domain.llm import LlmProvider
from ase.domain.users import User
from helpers import ADMIN_PASSWORD, USER_PASSWORD, bearer, login_token
from report_search_helpers import add_profile

PATH = "/api/admin/llm/models/discover"
BASE = "http://localhost:11434/v1"
DRAFT = {"provider": "openai_compatible", "base_url": BASE, "api_key": "draft-test-key"}


async def admin_headers(client, admin):
    return bearer(await login_token(client, admin.email, ADMIN_PASSWORD))


def discovery(container, *, side_effect=None):
    gateway = AsyncMock()
    gateway.list_models.return_value = ("model-z", "model-a", "model-z")
    gateway.list_models.side_effect = side_effect
    container.model_discovery = gateway
    return gateway.list_models


async def test_new_connection_lists_models_without_saving_a_profile_or_key(
    client: AsyncClient, container: Container, admin: User
) -> None:
    mock = discovery(container)
    async with container.session_factory() as session:
        before = await container.repositories(session).llm_profiles.list_all()
    response = await client.post(PATH, headers=await admin_headers(client, admin), json=DRAFT)
    assert response.status_code == 200, response.text
    assert response.json() == {"models": ["model-a", "model-z"]}
    assert DRAFT["api_key"] not in response.text
    mock.assert_awaited_once_with(BASE, DRAFT["api_key"])
    async with container.session_factory() as session:
        after = await container.repositories(session).llm_profiles.list_all()
    assert after == before


@pytest.mark.parametrize("authenticated", [False, True])
async def test_discovery_requires_admin_before_outbound_io(
    client: AsyncClient, container: Container, user: User, authenticated: bool
) -> None:
    mock = discovery(container)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD)) if authenticated else {}
    response = await client.post(PATH, headers=headers, json=DRAFT)
    assert response.status_code == (403 if authenticated else 401)
    mock.assert_not_awaited()


async def test_stored_key_is_reused_for_the_same_normalised_endpoint_only(
    client: AsyncClient, container: Container, admin: User
) -> None:
    async with container.session_factory() as session:
        profile = await add_profile(container, session)
    mock = discovery(container)
    payload = {"base_url": BASE + "/", "profile_id": str(profile.id)}
    headers = await admin_headers(client, admin)
    response = await client.post(PATH, headers=headers, json=payload)
    assert response.status_code == 200, response.text
    mock.assert_awaited_once_with(BASE, "test-key")
    mock.reset_mock()
    payload["base_url"] = "https://other.example/v1"
    refused = await client.post(PATH, headers=headers, json=payload)
    assert refused.status_code == 422, refused.text
    mock.assert_not_awaited()
    accepted = await client.post(PATH, headers=headers, json={**payload, "api_key": "new-key"})
    assert accepted.status_code == 200, accepted.text
    mock.assert_awaited_once_with(payload["base_url"], "new-key")
    async with container.session_factory() as session:
        unchanged = await container.repositories(session).llm_profiles.get(profile.id)
    assert unchanged is not None and unchanged.config_hash == profile.config_hash


async def test_other_provider_credential_cannot_be_reused(
    client: AsyncClient, container: Container, admin: User
) -> None:
    async with container.session_factory() as session:
        profile = await add_profile(container, session)
        profile.provider = LlmProvider.BEDROCK
        await container.repositories(session).llm_profiles.save(profile)
        await session.commit()
    mock = discovery(container)
    response = await client.post(
        PATH,
        headers=await admin_headers(client, admin),
        json={"base_url": BASE, "profile_id": str(profile.id)},
    )
    assert response.status_code == 422, response.text
    mock.assert_not_awaited()


async def test_missing_profile_never_triggers_discovery(
    client: AsyncClient, container: Container, admin: User
) -> None:
    mock = discovery(container)
    response = await client.post(
        PATH, headers=await admin_headers(client, admin), json={**DRAFT, "profile_id": str(uuid4())}
    )
    assert response.status_code == 404
    mock.assert_not_awaited()


@pytest.mark.parametrize("change", ["session", "profile"])
async def test_authority_and_profile_are_rechecked_after_outbound_io(
    client: AsyncClient, container: Container, admin: User, change: str
) -> None:
    async with container.session_factory() as session:
        profile = await add_profile(container, session)

    async def mutate(endpoint, key):
        async with container.session_factory() as session:
            repositories = container.repositories(session)
            if change == "session":
                current = await repositories.users.get_by_id(admin.id)
                current.security_version += 1
                await repositories.users.save(current)
            else:
                current = await repositories.llm_profiles.get(profile.id)
                current.model = "changed-model"
                await repositories.llm_profiles.save(current)
            await session.commit()
        return ("sensitive-model-name",)

    mock = discovery(container, side_effect=mutate)
    response = await client.post(
        PATH,
        headers=await admin_headers(client, admin),
        json={"base_url": BASE, "profile_id": str(profile.id)},
    )
    assert response.status_code == (401 if change == "session" else 422), response.text
    assert "sensitive-model-name" not in response.text
    mock.assert_awaited_once()


async def test_discovery_failure_does_not_echo_credentials_or_provider_errors(
    client: AsyncClient, container: Container, admin: User
) -> None:
    mock = discovery(container, side_effect=RuntimeError("draft-test-key secret-provider-error"))
    response = await client.post(PATH, headers=await admin_headers(client, admin), json=DRAFT)
    assert response.status_code == 422
    assert "draft-test-key" not in response.text and "secret-provider-error" not in response.text
    mock.assert_awaited_once()


@pytest.mark.parametrize("count", [1000, 1001])
async def test_catalogue_is_complete_within_bounds_and_rejects_overflow(
    client: AsyncClient, container: Container, admin: User, count: int
) -> None:
    mock = discovery(container)
    models = tuple(f"model-{index:04d}" for index in range(count))
    mock.return_value = models
    response = await client.post(PATH, headers=await admin_headers(client, admin), json=DRAFT)
    assert response.status_code == (200 if count == 1000 else 422), response.text
    if count == 1000:
        assert response.json() == {"models": list(models)}
    else:
        assert DRAFT["api_key"] not in response.text


async def test_malformed_catalogue_is_rejected_without_echoing_its_values(
    client: AsyncClient, container: Container, admin: User
) -> None:
    mock = discovery(container)
    mock.return_value = ("valid", "draft-test-key\n")
    response = await client.post(PATH, headers=await admin_headers(client, admin), json=DRAFT)
    assert response.status_code == 422
    assert "draft-test-key" not in response.text


async def test_discovery_deadline_bounds_slow_provider_io(
    client: AsyncClient, container: Container, admin: User, monkeypatch
) -> None:
    async def slow(endpoint, key):
        await asyncio.sleep(10)
        return ("never-returned",)

    discovery(container, side_effect=slow)
    monkeypatch.setattr(llm_discovery, "DISCOVERY_TIMEOUT_SECONDS", 0.001)
    response = await client.post(PATH, headers=await admin_headers(client, admin), json=DRAFT)
    assert response.status_code == 422
    assert "draft-test-key" not in response.text


async def test_invalid_endpoint_validation_never_echoes_credential_like_input(
    client: AsyncClient, container: Container, admin: User
) -> None:
    mock = discovery(container)
    response = await client.post(
        PATH,
        headers=await admin_headers(client, admin),
        json={**DRAFT, "base_url": "https://example.invalid:draft-test-key/v1"},
    )
    assert response.status_code == 422
    assert "draft-test-key" not in response.text
    mock.assert_not_awaited()
