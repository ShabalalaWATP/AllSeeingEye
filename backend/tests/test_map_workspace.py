"""Workspace authorisation, optimistic concurrency and hostile document boundaries."""

from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest

import ase.application.map_workspace as module
from ase.adapters.persistence.map_workspace import SqlMapWorkspaceRepository
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.map_workspace import validate_payload
from helpers import USER_PASSWORD, login_token
from team_helpers import CONTEXT
from test_report_team_scope import team_for
from test_saved_map_views import claims_for

DRAWINGS = {"version": 1, "objects": [], "selectedId": None}
RADIO = {"schemaVersion": 1, "draft": {"values": {"frequencyMHz": "150"}}}


async def create(container, claims, *, team_id=None, kind="drawings", payload=None):
    async with container.session_factory() as session:
        return await container.map_workspace(session).create(
            claims, kind, "Study", DRAWINGS if payload is None else payload, team_id, CONTEXT
        )


async def test_api_round_trip_conflict_and_deletion(client, container, user):
    token = await login_token(client, user.email, USER_PASSWORD)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"kind": "drawings", "title": "Study", "payload": DRAWINGS}
    response = await client.post("/api/map/workspaces", json=body, headers=headers)
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["revision"] == 1
    assert document["team_id"] is None
    assert response.headers["cache-control"] == "no-store"
    path = f"/api/map/workspaces/{document['id']}"
    listing = await client.get("/api/map/workspaces?kind=drawings", headers=headers)
    assert listing.json() == [document]
    assert (await client.get(path, headers=headers)).json() == document
    patch = {"title": "Updated", "payload": DRAWINGS, "expected_revision": 1}
    assert (await client.patch(path, json=patch, headers=headers)).json()["revision"] == 2
    assert (await client.patch(path, json=patch, headers=headers)).status_code == 409
    assert (await client.delete(path, headers=headers)).status_code == 204
    assert (await client.get(path, headers=headers)).status_code == 404
    assert (await client.get("/api/map/workspaces?kind=drawings", headers=headers)).json() == []


async def test_personal_scope_admin_override_and_scope_filtered_pagination(
    client, container, user, admin
):
    owner = await claims_for(client, container, user)
    administrator = await claims_for(client, container, admin)
    own = await create(container, owner)
    other = await create(container, administrator)
    async with container.session_factory() as session:
        service = container.map_workspace(session)
        assert [item.id for item in await service.list(owner, "drawings", 1)] == [own.id]
        assert await service.list(owner, "radio") == []
        assert (await service.get(administrator, own.id)).id == own.id
        with pytest.raises(NotFound):
            await service.get(owner, other.id)
    for operation in ("update", "remove"):
        async with container.session_factory() as session:
            service = container.map_workspace(session)
            with pytest.raises(NotFound):
                if operation == "update":
                    await service.update(owner, other.id, "no", DRAWINGS, 1, CONTEXT)
                else:
                    await service.remove(owner, other.id, CONTEXT)


async def test_pagination_reaches_records_across_more_than_one_scope(
    client, container, user, admin
):
    claims = await claims_for(client, container, user)
    team = await team_for(container, admin, user)
    personal = await create(container, claims)
    team_document = await create(container, claims, team_id=team.id)
    async with container.session_factory() as session:
        repository = SqlMapWorkspaceRepository(session)
        for index in range(100):
            source = personal if index < 50 else team_document
            await repository.create(replace(source, id=uuid4(), title=f"Drawing {index}"))
        await session.commit()
    async with container.session_factory() as session:
        service = container.map_workspace(session)
        first = await service.list(claims, "drawings", 100, 0)
        second = await service.list(claims, "drawings", 100, 100)
        assert len(first) == 100 and len(second) == 2
        assert len({document.id for document in first + second}) == 102


async def test_team_membership_archive_and_revoke(client, container, admin, user):
    team = await team_for(container, admin, user)
    claims = await claims_for(client, container, user)
    document = await create(container, claims, team_id=team.id)
    async with container.session_factory() as session:
        repo = SqlTeamRepository(session)
        await repo.save(replace(team, is_active=False))
        await session.commit()
    async with container.session_factory() as session:
        service = container.map_workspace(session)
        assert (await service.get(claims, document.id)).team_id == team.id
        with pytest.raises(Forbidden):
            await service.update(claims, document.id, "Archived", DRAWINGS, 1, CONTEXT)
    async with container.session_factory() as session:
        await SqlTeamRepository(session).remove_membership(team.id, user.id)
        await session.commit()
    async with container.session_factory() as session:
        service = container.map_workspace(session)
        assert await service.list(claims, "drawings") == []
        with pytest.raises(NotFound):
            await service.get(claims, document.id)


async def test_revoked_session_rejected_at_service_boundary(client, container, user):
    claims = await claims_for(client, container, user)
    document = await create(container, claims)
    async with container.session_factory() as session:
        await container.repositories(session).refresh_tokens.revoke_family(
            claims.family_id, container.clock.now()
        )
        await session.commit()
    for operation in ("list", "get", "create", "update", "remove"):
        async with container.session_factory() as session:
            service = container.map_workspace(session)
            with pytest.raises(Unauthenticated):
                if operation == "list":
                    await service.list(claims, "drawings")
                elif operation == "get":
                    await service.get(claims, document.id)
                elif operation == "create":
                    await service.create(claims, "drawings", "No", DRAWINGS, None, CONTEXT)
                elif operation == "update":
                    await service.update(claims, document.id, "No", DRAWINGS, 1, CONTEXT)
                else:
                    await service.remove(claims, document.id, CONTEXT)


async def test_conditional_write_failure_rolls_back(client, container, user, monkeypatch):
    claims = await claims_for(client, container, user)
    document = await create(container, claims)
    async with container.session_factory() as session:
        service = container.map_workspace(session)
        update = service.documents.update

        async def conflicting_update(candidate, revision):
            assert await update(candidate, revision)
            return False

        monkeypatch.setattr(service.documents, "update", conflicting_update)
        with pytest.raises(Conflict):
            await service.update(claims, document.id, "Lost", DRAWINGS, 1, CONTEXT)
    async with container.session_factory() as session:
        assert await container.map_workspace(session).get(claims, document.id) == document


async def test_quota_and_invalid_document_are_not_persisted(client, container, user, monkeypatch):
    claims = await claims_for(client, container, user)
    monkeypatch.setattr(module, "MAX_SCOPE_DOCUMENTS", 1)
    await create(container, claims)
    with pytest.raises(InvalidRequest, match="limit"):
        await create(container, claims)
    with pytest.raises(InvalidRequest):
        await create(container, claims, payload={"version": 1, "objects": ["bad"]})


@pytest.mark.parametrize(
    "payload",
    [
        {"version": 1, "objects": [], "raw_events": []},
        {"version": 1, "objects": [], "selectedId": "missing"},
        {"version": 2, "objects": []},
        {"version": 1, "objects": [None] * 51},
        {"version": 1, "objects": [], "selectedId": float("nan")},
        {"version": 1, "objects": [], "selectedId": "x" * 140000},
    ],
)
def test_drawing_payload_bounds(payload):
    with pytest.raises(ValueError):
        validate_payload("drawings", payload)


def test_valid_drawings_and_coordinate_rejection():
    obj = {
        "id": "one",
        "name": "Site",
        "shape": "point",
        "anchors": [[-1, 52]],
        "colour": "#abcdef",
        "visible": True,
        "locked": False,
        "notes": "",
    }
    payload = {"version": 1, "objects": [obj], "selectedId": "one"}
    validate_payload("drawings", payload)
    invalid = deepcopy(payload)
    invalid["objects"][0]["anchors"][0][0] = 181
    with pytest.raises(ValueError, match="coordinates"):
        validate_payload("drawings", invalid)


def test_radio_payload_finite_depth_and_unknown_kind():
    validate_payload("radio", RADIO)
    for payload in (
        {"schemaVersion": 1, "draft": {"a": float("inf")}},
        {"schemaVersion": 1, "draft": {}, "events": []},
        {"schemaVersion": 1, "draft": []},
    ):
        with pytest.raises(ValueError):
            validate_payload("radio", payload)
    nested = {}
    for _ in range(14):
        nested = {"x": nested}
    with pytest.raises(ValueError, match="complex"):
        validate_payload("radio", {"schemaVersion": 1, "draft": nested})
    with pytest.raises(ValueError, match="kind"):
        validate_payload("invalid", {})
