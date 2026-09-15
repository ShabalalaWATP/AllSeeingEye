"""Research Brief HTTP revisions remain scoped, bounded and strictly validated."""

from copy import deepcopy

from fastapi import FastAPI
from httpx import AsyncClient

from ase.application.research.brief_codec import brief_to_dict
from ase.container import Container
from ase.domain.teams import MembershipRole
from ase.domain.users import User
from helpers import ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from team_helpers import CONTEXT, team_service
from test_research_brief_persistence import _brief


def _draft() -> dict[str, object]:
    saved = brief_to_dict(_brief())
    identity = saved.pop("identity")
    return {
        "title": identity["title"],
        "team_id": None,
        "preset_id": None,
        "preset_version": None,
        **saved,
    }


async def test_create_read_revision_and_field_errors(
    client: AsyncClient, user: User, app: FastAPI
) -> None:
    assert "/api/research/briefs" in app.openapi()["paths"]
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    draft = _draft()
    endpoint = "/api/research/briefs"
    assert (await client.get(endpoint)).status_code == 401

    created = await client.post(endpoint, json=draft, headers=bearer(token))
    assert created.status_code == 201, created.text
    first = created.json()["brief"]
    brief_id = first["identity"]["id"]
    assert first["identity"]["owner_id"] == str(user.id)
    assert first["identity"]["revision"] == 1
    assert first["identity"]["origin"] == "authored"
    assert first["identity"]["published"] is False
    assert created.headers["Cache-Control"] == "private, no-store"

    listed = await client.get(endpoint + "?limit=1&offset=0", headers=bearer(token))
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == brief_id
    assert (await client.get(endpoint + "?limit=101", headers=bearer(token))).status_code == 422
    assert (await client.get(endpoint + "?offset=-1", headers=bearer(token))).status_code == 422
    assert (await client.get(f"{endpoint}/{brief_id}/revisions/1", headers=bearer(token))).json()[
        "brief"
    ] == first

    edited = deepcopy(draft)
    edited["base_revision"] = 1
    edited["title"] = "Updated regional developments"
    edited["question"]["main"] = "What changed since the last assessment?"
    revised = await client.post(
        f"{endpoint}/{brief_id}/revisions", json=edited, headers=bearer(token)
    )
    assert revised.status_code == 201, revised.text
    second = revised.json()["brief"]
    assert second["identity"]["revision"] == 2
    assert second["identity"]["id"] == brief_id
    assert second["identity"]["title"] == edited["title"]
    assert (await client.get(f"{endpoint}/{brief_id}/revisions/1", headers=bearer(token))).json()[
        "brief"
    ] == first
    assert (await client.get(f"{endpoint}/{brief_id}", headers=bearer(token))).json()[
        "brief"
    ] == second
    history = await client.get(f"{endpoint}/{brief_id}/revisions?limit=1", headers=bearer(token))
    assert history.status_code == 200
    assert [item["revision"] for item in history.json()["items"]] == [2]
    assert (
        await client.post(f"{endpoint}/{brief_id}/revisions", json=edited, headers=bearer(token))
    ).status_code == 409
    assert (await client.delete(f"{endpoint}/{brief_id}", headers=bearer(token))).status_code == 405

    invalid = deepcopy(draft)
    invalid["question"]["main"] = "PRIVATE_SENTINEL" * 150
    failure = await client.post(endpoint, json=invalid, headers=bearer(token))
    assert failure.status_code == 422
    assert "question.main" in failure.json()["error"]["fields"]
    assert "PRIVATE_SENTINEL" not in failure.text
    spoof = {**draft, "identity": {"owner_id": "forged"}}
    assert (await client.post(endpoint, json=spoof, headers=bearer(token))).status_code == 422


async def test_team_reader_and_administrator_scope(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    reader = await create_user(
        container, email="brief-reader@example.com", password="another-long-passphrase"
    )
    outsider = await create_user(
        container, email="brief-outsider@example.com", password="another-long-passphrase"
    )
    async with team_service(container) as service:
        team = await service.create(admin, "Research desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
        await service.set_member(
            admin, team.id, email=reader.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    owner_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    reader_token = await login_token(client, reader.email, "another-long-passphrase")
    outsider_token = await login_token(client, outsider.email, "another-long-passphrase")
    admin_token = await login_token(client, admin.email, ADMIN_PASSWORD)
    draft = {**_draft(), "team_id": str(team.id)}
    endpoint = "/api/research/briefs"
    created = await client.post(endpoint, json=draft, headers=bearer(owner_token))
    assert created.status_code == 201, created.text
    brief_id = created.json()["brief"]["identity"]["id"]
    assert (
        await client.get(f"{endpoint}/{brief_id}", headers=bearer(reader_token))
    ).status_code == 200
    assert (
        await client.get(f"{endpoint}/{brief_id}", headers=bearer(admin_token))
    ).status_code == 200
    assert (
        await client.get(f"{endpoint}/{brief_id}", headers=bearer(outsider_token))
    ).status_code == 404
    assert (await client.get(endpoint, headers=bearer(outsider_token))).json()["items"] == []
    assert (await client.get(endpoint, headers=bearer(reader_token))).json()["items"][0][
        "id"
    ] == brief_id

    edit = {**draft, "base_revision": 1}
    assert (
        await client.post(
            f"{endpoint}/{brief_id}/revisions", json=edit, headers=bearer(reader_token)
        )
    ).status_code == 403
    async with container.session_factory() as session:
        current_admin = await container.repositories(session).users.get_by_id(admin.id)
    assert current_admin is not None
    async with team_service(container) as service:
        await service.remove_member(current_admin, team.id, reader.id, CONTEXT)
    assert (
        await client.get(f"{endpoint}/{brief_id}", headers=bearer(reader_token))
    ).status_code == 404
