"""Native provider profile rules and backwards-compatible saved test receipts."""

import hashlib
import json
from dataclasses import replace
from uuid import UUID

import pytest
from httpx import AsyncClient

from ase.api.schemas_llm import LlmProfileIn
from ase.container import Container
from ase.domain.bedrock import normalise_bedrock_base_url
from ase.domain.errors import InvalidRequest
from ase.domain.llm import LlmProvider
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_llm import FakeGateway
from test_llm_connections import DRAFT, ROOT, draft, proof
from test_llm_key_boundaries import synthetic_key

BEDROCK = {
    **DRAFT,
    "provider": "bedrock",
    "base_url": "https://bedrock-runtime.us-east-1.amazonaws.com",
    "model": "anthropic.fixture-model-v1:0",
    "reasoning_effort": None,
    "api_key": synthetic_key(4_096),
}


def test_application_rejects_raw_provider_strings_that_would_skip_native_rules() -> None:
    profile = LlmProfileIn.model_validate(BEDROCK).to_input()
    with pytest.raises(InvalidRequest):
        replace(profile, provider="bedrock", base_url="https://other.example/v1")


@pytest.mark.parametrize(
    "root",
    [
        "https://bedrock-runtime.us-east-1.amazonaws.com",
        "https://bedrock-runtime.eu-west-2.amazonaws.com/",
        "https://bedrock-runtime.us-gov-west-1.amazonaws.com",
    ],
)
def test_native_endpoint_is_a_canonical_regional_runtime_root(root: str) -> None:
    assert normalise_bedrock_base_url(root) == root.rstrip("/")


@pytest.mark.parametrize(
    "root",
    [
        "http://bedrock-runtime.us-east-1.amazonaws.com",
        "https://bedrock-runtime.us-east-1.amazonaws.com:443",
        "https://bedrock-runtime.us-east-1.amazonaws.com/v1",
        "https://bedrock-runtime.us-east-1.amazonaws.com?key=fixture",
        "https://bedrock-runtime.us-east-1.amazonaws.com#fragment",
        "https://user@bedrock-runtime.us-east-1.amazonaws.com",
        "https://bedrock-runtime.us-east-1.amazonaws.com.attacker.test",
        "https://bedrock.us-east-1.amazonaws.com",
        "https://127.0.0.1",
    ],
)
def test_native_endpoint_rejects_non_runtime_destinations(root: str) -> None:
    with pytest.raises(ValueError):
        normalise_bedrock_base_url(root)


async def test_native_save_test_propagation_and_manual_model_discovery(
    client: AsyncClient, container: Container, admin: User
) -> None:
    class NoDiscovery:
        async def list_models(self, base_url: str, api_key: str) -> tuple[str, ...]:
            pytest.fail("Native profiles must not send bearer keys to model discovery.")

    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    container.model_discovery = NoDiscovery()
    gateway = FakeGateway()
    container.llm = gateway
    created = await client.post(f"{ROOT}/profiles", headers=headers, json=BEDROCK)
    assert created.status_code == 201, created.text
    profile = created.json()
    assert profile["provider"] == "bedrock" and not profile["enabled"]
    assert BEDROCK["api_key"] not in created.text and not gateway.calls
    receipt = await proof(client, headers, profile)
    assert receipt["tested_config_hash"]
    assert gateway.calls[0][3].provider is LlmProvider.BEDROCK
    assert gateway.calls[0][3].reasoning_effort is None
    assert gateway.calls[0][1] == BEDROCK["api_key"]
    result = await client.get(f"{ROOT}/profiles/{profile['id']}/models", headers=headers)
    assert result.status_code == 422 and "manually" in result.text
    assert BEDROCK["api_key"] not in result.text


@pytest.mark.parametrize(
    "change",
    [
        {"reasoning_effort": "max"},
        {"roles": ["embeddings"]},
        {"api_key": ""},
        {"provider": "unknown"},
        {"base_url": "https://other.example/v1"},
        {"temperature": 1.01},
        {"model": "m" * 2049},
    ],
)
async def test_invalid_native_configuration_rejected_before_persistence(
    client: AsyncClient, container: Container, admin: User, change: dict
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    response = await client.post(f"{ROOT}/profiles", headers=headers, json={**BEDROCK, **change})
    assert response.status_code == 422
    async with container.session_factory() as session:
        assert not await container.repositories(session).llm_profiles.list_all()


async def test_provider_switch_requires_new_key_even_at_the_same_base_url(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    container.llm = FakeGateway()
    created = await client.post(f"{ROOT}/profiles", headers=headers, json=BEDROCK)
    profile = created.json()
    await proof(client, headers, profile)
    path = f"{ROOT}/profiles/{profile['id']}"
    blank = {**BEDROCK, "provider": "openai_compatible", "api_key": ""}
    assert (await client.put(path, headers=headers, json=blank)).status_code == 422
    async with container.session_factory() as session:
        saved = await container.repositories(session).llm_profiles.get(UUID(profile["id"]))
        assert saved is not None and saved.is_tested and saved.revision == 1
    rotated = await client.put(
        path, headers=headers, json={**blank, "api_key": synthetic_key(4_096, "b")}
    )
    assert rotated.status_code == 200
    assert rotated.json()["provider"] == "openai_compatible"
    assert rotated.json()["revision"] == 2 and not rotated.json()["is_tested"]


async def test_legacy_openai_configuration_hash_remains_byte_identical(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    profile = await draft(client, headers)
    async with container.session_factory() as session:
        saved = await container.repositories(session).llm_profiles.get(UUID(profile["id"]))
        assert saved is not None
        legacy_values = (
            str(saved.id),
            saved.revision,
            saved.name,
            saved.base_url,
            saved.model,
            saved.api_key_encrypted,
            sorted(saved.roles),
            saved.max_output_tokens,
            saved.temperature,
            saved.reasoning_effort,
        )
        legacy_hash = hashlib.sha256(
            json.dumps(legacy_values, separators=(",", ":")).encode()
        ).hexdigest()
        assert saved.provider is LlmProvider.OPENAI_COMPATIBLE and saved.config_hash == legacy_hash
        assert replace(saved, provider=LlmProvider.BEDROCK).config_hash != legacy_hash


async def test_native_long_model_identifier_accepts_2048_but_openai_stays_at_120(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    identifier = "arn:aws:bedrock:us-east-1:123456789012:application-inference-profile/"
    identifier += "a" * (2048 - len(identifier))
    created = await client.post(
        f"{ROOT}/profiles", headers=headers, json={**BEDROCK, "model": identifier, "temperature": 1}
    )
    assert created.status_code == 201, created.text
    assert created.json()["model"] == identifier
    async with container.session_factory() as session:
        stored = await container.repositories(session).llm_profiles.get(UUID(created.json()["id"]))
        assert stored is not None and stored.model == identifier
    rejected = await client.post(
        f"{ROOT}/profiles",
        headers=headers,
        json={**DRAFT, "name": "Invalid OpenAI", "model": "m" * 121},
    )
    assert rejected.status_code == 422
