"""Migration compatibility cannot bypass explicit new connection activation."""

from uuid import UUID

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_llm import FakeGateway
from test_llm_connections import DRAFT, ROOT, activation, draft, proof


async def test_text_crud_cannot_enable_untested_models_but_embeddings_remain_supported(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    response = await client.post(
        f"{ROOT}/profiles", headers=headers, json={**DRAFT, "enabled": True}
    )
    assert response.status_code == 201 and not response.json()["enabled"]
    profile_id = response.json()["id"]
    edited = await client.put(
        f"{ROOT}/profiles/{profile_id}", headers=headers, json={**DRAFT, "enabled": True}
    )
    assert edited.status_code == 200 and not edited.json()["enabled"]
    embedding = await client.post(
        f"{ROOT}/profiles",
        headers=headers,
        json={
            **DRAFT,
            "name": "Embedding",
            "roles": ["embeddings"],
            "enabled": True,
            "reasoning_effort": None,
        },
    )
    assert embedding.status_code == 201 and embedding.json()["enabled"]


async def test_legacy_enabled_configuration_stays_immutable_until_global_replacement(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    legacy = await draft(client, headers, "Legacy")
    # Model a migrated enabled legacy row. Migration itself preserves this value.
    async with container.session_factory() as session:
        r = container.repositories(session)
        stored = await r.llm_profiles.get(UUID(legacy["id"]))
        assert stored is not None
        stored.enabled = True
        await r.llm_profiles.save(stored)
        await r.uow.commit()
    path = f"{ROOT}/profiles/{legacy['id']}"
    assert (await client.put(path, headers=headers, json=DRAFT)).status_code == 422
    assert (await client.delete(path, headers=headers)).status_code == 422
    replacement = await draft(client, headers, "Replacement")
    container.llm = FakeGateway()
    receipt = await proof(client, headers, replacement)
    applied = await client.put(
        f"{ROOT}/connections", headers=headers, json=activation(replacement, receipt)
    )
    assert applied.status_code == 200
    edited = await client.put(path, headers=headers, json=DRAFT)
    assert edited.status_code == 200 and not edited.json()["enabled"]
    assert (await client.delete(path, headers=headers)).status_code == 204
