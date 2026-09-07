"""Administrator-only tested personal workspace activation and safe resets."""

from uuid import uuid4

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_llm import FakeGateway
from test_llm_connections import ROOT, activation, draft, proof


async def test_personal_activation_requires_global_and_preserves_cas(
    client: AsyncClient, container: Container, admin: User, user: User
):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    container.llm = FakeGateway()
    item = await draft(client, headers)
    tested = await proof(client, headers, item)
    personal = {**activation(item, tested), "user_id": str(user.id)}
    assert (
        await client.put(f"{ROOT}/connections", headers=headers, json=personal)
    ).status_code == 422
    assert (
        await client.put(f"{ROOT}/connections", headers=headers, json=activation(item, tested))
    ).status_code == 200
    first = await client.put(f"{ROOT}/connections", headers=headers, json=personal)
    assert first.status_code == 200, first.text
    binding = first.json()
    assert binding["user_id"] == str(user.id) and binding["team_id"] is None
    assert (
        await client.put(f"{ROOT}/connections", headers=headers, json=personal)
    ).status_code == 422
    reset = f"{ROOT}/connections/user/{user.id}?expected_revision={binding['revision']}"
    assert (await client.delete(reset, headers=headers)).status_code == 204
    second = await client.put(f"{ROOT}/connections", headers=headers, json=personal)
    assert second.status_code == 200 and second.json()["revision"] > binding["revision"]
    assert (await client.delete(reset, headers=headers)).status_code == 422
    items = (await client.get(f"{ROOT}/connections", headers=headers)).json()["items"]
    assert len(items) == 2 and sum(item["user_id"] is None for item in items) == 1
    assert (
        await client.delete(f"{ROOT}/profiles/{item['id']}", headers=headers)
    ).status_code == 422


async def test_personal_activation_validates_target_and_admin_access(
    client: AsyncClient, container: Container, admin: User, user: User
):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    member = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    container.llm = FakeGateway()
    item = await draft(client, headers)
    tested = await proof(client, headers, item)
    base = activation(item, tested)
    await client.put(f"{ROOT}/connections", headers=headers, json=base)
    assert (
        await client.put(
            f"{ROOT}/connections", headers=member, json={**base, "user_id": str(user.id)}
        )
    ).status_code == 403
    assert (
        await client.delete(
            f"{ROOT}/connections/user/{user.id}?expected_revision=1", headers=member
        )
    ).status_code == 403
    assert (
        await client.put(
            f"{ROOT}/connections", headers=headers, json={**base, "user_id": str(uuid4())}
        )
    ).status_code == 404
    assert (
        await client.put(
            f"{ROOT}/connections",
            headers=headers,
            json={**base, "user_id": str(user.id), "team_id": str(uuid4())},
        )
    ).status_code == 422
    async with container.session_factory() as session:
        repos = container.repositories(session)
        target = await repos.users.get_by_id(user.id)
        target.is_active = False
        await repos.users.save(target)
        await session.commit()
    assert (
        await client.put(
            f"{ROOT}/connections", headers=headers, json={**base, "user_id": str(user.id)}
        )
    ).status_code == 422
