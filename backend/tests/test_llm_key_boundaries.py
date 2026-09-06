"""Long synthetic bearer credentials stay bounded, encrypted and write-only."""

from dataclasses import replace
from uuid import UUID

import pytest
from httpx import AsyncClient

from ase.api.schemas_llm import LlmProfileIn
from ase.container import Container
from ase.domain.errors import InvalidRequest
from ase.domain.llm import MAX_API_KEY_LENGTH
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_llm_connections import DRAFT, ROOT


def synthetic_key(length: int, fill: str = "a") -> str:
    prefix = "fixture-bearer-"
    return prefix + fill * (length - len(prefix))


@pytest.mark.parametrize("length", [4_096, MAX_API_KEY_LENGTH])
async def test_long_keys_save_and_rotate_without_secret_readback(
    client: AsyncClient, container: Container, admin: User, length: int
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    first_key = synthetic_key(length)
    created = await client.post(
        f"{ROOT}/profiles", headers=headers, json={**DRAFT, "api_key": first_key}
    )
    assert created.status_code == 201, created.text
    assert first_key not in created.text and "api_key_encrypted" not in created.text
    profile_id = UUID(created.json()["id"])
    async with container.session_factory() as session:
        saved = await container.repositories(session).llm_profiles.get(profile_id)
        assert saved is not None
        assert container.cipher.decrypt(saved.api_key_encrypted) == first_key
        assert first_key not in saved.api_key_encrypted and first_key not in repr(saved)
    next_key = synthetic_key(length, "b")
    updated = await client.put(
        f"{ROOT}/profiles/{profile_id}", headers=headers, json={**DRAFT, "api_key": next_key}
    )
    assert updated.status_code == 200 and updated.json()["revision"] == 2
    assert next_key not in updated.text and first_key not in updated.text
    listed = await client.get(f"{ROOT}/profiles", headers=headers)
    assert next_key not in listed.text and first_key not in listed.text
    async with container.session_factory() as session:
        saved = await container.repositories(session).llm_profiles.get(profile_id)
        assert saved is not None
        assert container.cipher.decrypt(saved.api_key_encrypted) == next_key
        assert next_key not in repr(saved)
        assert not await container.repositories(session).llm_usage.list_recent(10)


async def test_oversized_create_and_update_reject_without_mutating_saved_profile(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await client.post(
        f"{ROOT}/profiles", headers=headers, json={**DRAFT, "api_key": synthetic_key(4_096)}
    )
    assert created.status_code == 201
    profile_id = UUID(created.json()["id"])
    async with container.session_factory() as session:
        before = await container.repositories(session).llm_profiles.get(profile_id)
        assert before is not None
    oversized = synthetic_key(MAX_API_KEY_LENGTH + 1)
    invalid = {**DRAFT, "name": "Rejected revision", "api_key": oversized}
    for method, path in (("POST", f"{ROOT}/profiles"), ("PUT", f"{ROOT}/profiles/{profile_id}")):
        response = await client.request(method, path, headers=headers, json=invalid)
        assert response.status_code == 422
        assert oversized not in response.text and "fixture-bearer-" not in response.text
    async with container.session_factory() as session:
        profiles = await container.repositories(session).llm_profiles.list_all()
        assert profiles == [before]


async def test_long_saved_key_is_preserved_only_for_the_same_destination(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    key = synthetic_key(MAX_API_KEY_LENGTH)
    created = await client.post(f"{ROOT}/profiles", headers=headers, json={**DRAFT, "api_key": key})
    assert created.status_code == 201
    profile_id = UUID(created.json()["id"])
    blank = {**DRAFT, "api_key": ""}
    kept = await client.put(f"{ROOT}/profiles/{profile_id}", headers=headers, json=blank)
    assert kept.status_code == 200
    changed = {**blank, "base_url": "https://other.example/v1"}
    rejected = await client.put(f"{ROOT}/profiles/{profile_id}", headers=headers, json=changed)
    assert rejected.status_code == 422 and key not in rejected.text
    async with container.session_factory() as session:
        saved = await container.repositories(session).llm_profiles.get(profile_id)
        assert saved is not None
        assert saved.revision == 2 and saved.base_url == DRAFT["base_url"].rstrip("/")
        assert container.cipher.decrypt(saved.api_key_encrypted) == key


def test_application_input_enforces_the_same_limit_and_masks_repr() -> None:
    key = synthetic_key(MAX_API_KEY_LENGTH)
    schema = LlmProfileIn.model_validate({**DRAFT, "api_key": key})
    data = schema.to_input()
    assert data.api_key == key and key not in repr(data) and key not in repr(schema)
    with pytest.raises(InvalidRequest, match="settings are invalid"):
        replace(data, api_key=key + "a")
