"""Synthetic API tests of explicit tested activation and credential boundaries."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from ase.container import Container
from ase.domain.llm import TEXT_ROLES, ReasoningEffort, normalise_base_url
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_llm import PROFILE, FakeGateway

ROOT = "/api/admin/llm"
DRAFT = {
    **PROFILE,
    "roles": sorted(TEXT_ROLES),
    "enabled": False,
    "reasoning_effort": "max",
    "max_output_tokens": 16_000,
}


async def draft(client: AsyncClient, headers: dict[str, str], name: str = "Draft") -> dict:
    response = await client.post(f"{ROOT}/profiles", json={**DRAFT, "name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def proof(client: AsyncClient, headers: dict[str, str], profile: dict) -> dict:
    response = await client.post(f"{ROOT}/profiles/{profile['id']}/test", headers=headers)
    assert response.status_code == 200 and response.json()["ok"], response.text
    return response.json()


def activation(
    profile: dict, receipt: dict, *, team_id: str | None = None, expected: int | None = None
) -> dict:
    return {
        "profile_id": profile["id"],
        "team_id": team_id,
        "expected_profile_revision": receipt["revision"],
        "tested_config_hash": receipt["tested_config_hash"],
        "expected_binding_revision": expected,
    }


async def test_draft_test_apply_and_bound_immutability(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    gateway = FakeGateway()
    container.llm = gateway
    profile = await draft(client, headers)
    assert not profile["enabled"] and not profile["is_tested"] and not gateway.calls
    invalid = await client.put(
        f"{ROOT}/connections",
        headers=headers,
        json={
            "profile_id": profile["id"],
            "expected_profile_revision": 1,
            "tested_config_hash": "0" * 64,
        },
    )
    assert invalid.status_code == 422
    receipt = await proof(client, headers, profile)
    request = gateway.calls[0][3]
    assert request.reasoning_effort is ReasoningEffort.MAX and request.max_output_tokens == 16_000
    applied = await client.put(
        f"{ROOT}/connections", headers=headers, json=activation(profile, receipt)
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["profile_revision"] == receipt["revision"]
    listed = (await client.get(f"{ROOT}/profiles", headers=headers)).json()["items"][0]
    assert listed["enabled"] and listed["is_tested"] and listed["is_bound"]
    assert listed["tested_config_hash"] == receipt["tested_config_hash"]
    assert (
        await client.put(f"{ROOT}/profiles/{profile['id']}", headers=headers, json=DRAFT)
    ).status_code == 422
    assert (
        await client.delete(f"{ROOT}/profiles/{profile['id']}", headers=headers)
    ).status_code == 422
    assert (
        await client.put(f"{ROOT}/connections", headers=headers, json=activation(profile, receipt))
    ).status_code == 422
    # Latest failed probe invalidates NEW activations without removing the saved binding.
    container.llm = FakeGateway(content='{"ok": 1}')
    failed = await client.post(f"{ROOT}/profiles/{profile['id']}/test", headers=headers)
    assert not failed.json()["ok"] and failed.json()["tested_config_hash"] is None
    assert (
        await client.put(
            f"{ROOT}/connections",
            headers=headers,
            json=activation(profile, receipt, expected=applied.json()["revision"]),
        )
    ).status_code == 422
    assert len((await client.get(f"{ROOT}/connections", headers=headers)).json()["items"]) == 1


async def test_team_requires_global_and_reset_does_not_reuse_confirmation_revision(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    container.llm = FakeGateway()
    first, second = await draft(client, headers, "First"), await draft(client, headers, "Second")
    first_proof, second_proof = (
        await proof(client, headers, first),
        await proof(client, headers, second),
    )
    team = await client.post("/api/teams", headers=headers, json={"name": "Team"})
    assert team.status_code == 201, team.text
    team_id = team.json()["id"]
    assert (
        await client.put(
            f"{ROOT}/connections",
            headers=headers,
            json=activation(first, first_proof, team_id=team_id),
        )
    ).status_code == 422
    global_binding = await client.put(
        f"{ROOT}/connections", headers=headers, json=activation(first, first_proof)
    )
    assert global_binding.status_code == 200
    original = await client.put(
        f"{ROOT}/connections", headers=headers, json=activation(first, first_proof, team_id=team_id)
    )
    old_revision = original.json()["revision"]
    reset = f"{ROOT}/connections/team/{team_id}?expected_revision={old_revision}"
    assert (await client.delete(reset, headers=headers)).status_code == 204
    replacement = await client.put(
        f"{ROOT}/connections",
        headers=headers,
        json=activation(second, second_proof, team_id=team_id),
    )
    assert replacement.status_code == 200 and replacement.json()["revision"] > old_revision
    assert (await client.delete(reset, headers=headers)).status_code == 422
    assert (
        await client.put(
            f"{ROOT}/connections",
            headers=headers,
            json=activation(first, first_proof, team_id=team_id, expected=old_revision),
        )
    ).status_code == 422
    items = (await client.get(f"{ROOT}/connections", headers=headers)).json()["items"]
    assert next(item for item in items if item["team_id"] == team_id)["profile_id"] == second["id"]


@pytest.mark.parametrize(
    "change",
    [
        {"model": "replacement"},
        {"reasoning_effort": "low"},
        {"api_key": "replacement-key"},
        {"temperature": 0.9},
    ],
)
async def test_edit_invalidates_the_entire_test_receipt(
    client: AsyncClient, container: Container, admin: User, change: dict
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    container.llm = FakeGateway()
    profile = await draft(client, headers)
    receipt = await proof(client, headers, profile)
    changed = await client.put(
        f"{ROOT}/profiles/{profile['id']}", headers=headers, json={**DRAFT, **change}
    )
    assert changed.status_code == 200 and changed.json()["revision"] == 2
    assert not changed.json()["is_tested"] and changed.json()["tested_at"] is None
    assert (
        await client.put(f"{ROOT}/connections", headers=headers, json=activation(profile, receipt))
    ).status_code == 422


@pytest.mark.parametrize(
    "destination", ["https://other.example/v1", "http://localhost:11434/other"]
)
async def test_saved_key_never_follows_a_changed_credential_destination(
    client: AsyncClient, container: Container, admin: User, destination: str
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    profile = await draft(client, headers)
    changed = {**DRAFT, "base_url": destination, "api_key": ""}
    assert (
        await client.put(f"{ROOT}/profiles/{profile['id']}", headers=headers, json=changed)
    ).status_code == 422
    changed["api_key"] = "explicit-new-key"
    assert (
        await client.put(f"{ROOT}/profiles/{profile['id']}", headers=headers, json=changed)
    ).status_code == 200


@pytest.mark.parametrize(
    "url",
    [
        "https://host/v1?secret=x",
        "https://host/v1#x",
        "http://host:invalid/v1",
        "http://host/\npath",
    ],
)
def test_unsafe_endpoint_forms_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        normalise_base_url(url)


async def test_discovery_saved_secret_safe_errors_and_non_admin_denial(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    class Discovery:
        fail = False
        malformed = False

        async def list_models(self, base_url: str, api_key: str) -> tuple[str, ...]:
            assert api_key == DRAFT["api_key"]
            if self.fail:
                raise RuntimeError("DO NOT EXPOSE " + api_key)
            return ("z", "a", "a", "bad\nname") if self.malformed else ("z", "a", "a")

    discovery = Discovery()
    container.model_discovery = discovery
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    profile = await draft(client, headers)
    path = f"{ROOT}/profiles/{profile['id']}/models"
    result = await client.get(path, headers=headers)
    assert result.json() == {"models": ["a", "z"]}
    discovery.malformed = True
    malformed = await client.get(path, headers=headers)
    assert malformed.status_code == 422
    assert "bad" not in malformed.text and DRAFT["api_key"] not in malformed.text
    discovery.malformed = False
    discovery.fail = True
    failed = await client.get(path, headers=headers)
    assert failed.status_code == 422 and "DO NOT EXPOSE" not in failed.text
    other_headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    assert (await client.get(path, headers=other_headers)).status_code == 403
    assert (await client.get(f"{ROOT}/connections", headers=other_headers)).status_code == 403
    assert (
        await client.get(f"{ROOT}/profiles/{uuid4()}/models", headers=headers)
    ).status_code == 404
    async with container.session_factory() as session:
        saved = await container.repositories(session).llm_profiles.get(UUID(profile["id"]))
        assert saved is not None and DRAFT["api_key"] not in repr(saved)


async def test_activation_rejects_wrong_capability_archived_and_missing_scopes(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    container.llm = FakeGateway()
    response = await client.post(
        f"{ROOT}/profiles", headers=headers, json={**DRAFT, "roles": ["assessment"]}
    )
    profile = response.json()
    receipt = await proof(client, headers, profile)
    body = activation(profile, receipt)
    assert (await client.put(f"{ROOT}/connections", headers=headers, json=body)).status_code == 422
    missing = str(uuid4())
    assert (
        await client.put(
            f"{ROOT}/connections", headers=headers, json={**body, "profile_id": missing}
        )
    ).status_code == 404
    assert (
        await client.put(f"{ROOT}/connections", headers=headers, json={**body, "team_id": missing})
    ).status_code == 404
    assert (
        await client.delete(
            f"{ROOT}/connections/team/{missing}?expected_revision=1", headers=headers
        )
    ).status_code == 404
    created = await client.post("/api/teams", headers=headers, json={"name": "Archived"})
    team_id = created.json()["id"]
    assert (
        await client.delete(
            f"{ROOT}/connections/team/{team_id}?expected_revision=1", headers=headers
        )
    ).status_code == 404
    archived = await client.patch(
        f"/api/teams/{team_id}", headers=headers, json={"is_active": False}
    )
    assert archived.status_code == 200
    assert (
        await client.put(f"{ROOT}/connections", headers=headers, json={**body, "team_id": team_id})
    ).status_code == 422
