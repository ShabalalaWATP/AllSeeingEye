"""KAN-120/KAN-124: named live map views and ops-room playlists as workspace documents."""

from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest

import ase.application.map_workspace as module
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.domain.collection import CollectionPlan
from ase.domain.errors import Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.map_workspace import validate_payload
from board_subject_helpers import seed_area
from feeds_helpers import NOW
from helpers import USER_PASSWORD, login_token
from team_helpers import CONTEXT
from test_report_team_scope import team_for
from test_saved_map_views import claims_for

VIEW = {
    "version": 1,
    "projection": "globe",
    "camera": {"center": [24.5, 57.2], "zoom": 4.5, "bearing": 0, "pitch": 0},
    "base_layer": "dark",
    "layers": ["aviation", "aircraft", "interference"],
    "window_hours": 24,
    "nation": None,
    "filters": {"flight": "military", "gnss_level": "red", "gnss_minimum": 10},
    "plan_id": None,
}


def playlist(*entries):
    return {"version": 1, "entries": list(entries)}


def entry(kind, identity, caption="Baltic", dwell=30):
    return {"kind": kind, "id": str(identity), "caption": caption, "dwell_seconds": dwell}


async def make(container, claims, kind="live_view", payload=None, team_id=None):
    async with container.session_factory() as session:
        return await container.map_workspace(session).create(
            claims, kind, "Baltic watch", VIEW if payload is None else payload, team_id, CONTEXT
        )


async def test_live_view_api_round_trip_revision_guard_and_audit(client, container, user):
    token = await login_token(client, user.email, USER_PASSWORD)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"kind": "live_view", "title": "Baltic watch", "payload": VIEW}
    created = await client.post("/api/map/workspaces", json=body, headers=headers)
    assert created.status_code == 201, created.text
    document = created.json()
    assert document["kind"] == "live_view" and document["payload"] == VIEW
    listing = await client.get("/api/map/workspaces?kind=live_view", headers=headers)
    assert listing.json() == [document]
    assert (await client.get("/api/map/workspaces?kind=drawings", headers=headers)).json() == []
    path = f"/api/map/workspaces/{document['id']}"
    patch = {"title": "Baltic 24h", "payload": VIEW, "expected_revision": 1}
    assert (await client.patch(path, json=patch, headers=headers)).json()["revision"] == 2
    stale = await client.patch(path, json=patch, headers=headers)
    assert stale.status_code == 409
    async with container.session_factory() as session:
        entries = await container.repositories(session).audit.list_before(None, 20)
    changes = [e for e in entries if e.action.value == "map_workspace_changed"]
    assert {(e.details["operation"], e.details["kind"]) for e in changes} == {
        ("create", "live_view"),
        ("update", "live_view"),
    }


@pytest.mark.parametrize(
    "change",
    [
        {"layers": ["aviation", "retired_layer"]},
        {"layers": ["aviation", "aviation"]},
        {"filters": {"unknown_filter": "all"}},
        {"filters": {"flight": "civil"}},
        {"filters": {"gnss_minimum": 7}},
        {"filters": {"cyber_query": "x" * 101}},
        {"filters": {"conflict_historical": "yes"}},
        {"projection": "mercator"},
        {"base_layer": "retired"},
        {"camera": {"center": [181, 0], "zoom": 2, "bearing": 0, "pitch": 0}},
        {"camera": {"center": [0, 0], "zoom": 23, "bearing": 0, "pitch": 0}},
        {"camera": {"center": [0, 0], "zoom": 2, "bearing": 0, "pitch": 0, "raw": 1}},
        {"window_hours": 0},
        {"window_hours": 10_000},
        {"window_hours": True},
        {"nation": "gb"},
        {"plan_id": "not-a-uuid"},
        {"area_id": None},
        {"events": [{"id": "raw"}]},
        {"version": 2},
    ],
)
def test_live_view_rejects_unknown_ids_and_live_data(change):
    payload = {**deepcopy(VIEW), **change}
    with pytest.raises(ValueError):
        validate_payload("live_view", payload)


def test_live_view_accepts_every_known_layer_and_filter():
    payload = deepcopy(VIEW)
    payload.update(
        projection="map",
        nation="GB",
        window_hours=None,
        layers=[
            "news",
            "conflict",
            "disaster",
            "aviation",
            "maritime",
            "space",
            "cyber",
            "social",
            "political",
            "humanitarian",
            "economic",
            "aircraft",
            "vessels",
            "firms",
            "fires",
            "interference",
            "terminator",
        ],
        filters={
            "quality": "reported",
            "flight": "all",
            "vessel": "military",
            "gnss_level": "all",
            "gnss_minimum": 50,
            "cyber_kind": "ransomware_claim",
            "cyber_query": "lockbit",
            "conflict_group": "strikes",
            "conflict_historical": True,
            "conflict_unreviewed": False,
            "conflict_precision": "exact",
        },
    )
    validate_payload("live_view", payload)


@pytest.mark.parametrize(
    "payload",
    [
        playlist(*[entry("view", uuid4()) for _ in range(9)]),
        playlist(entry("report", uuid4())),
        playlist(entry("view", "nope")),
        playlist(entry("view", uuid4(), dwell=4)),
        playlist(entry("view", uuid4(), dwell=3601)),
        playlist(entry("view", uuid4(), caption="x" * 121)),
        {"version": 1, "entries": [], "events": []},
        {"version": 1, "entries": [{**entry("area", uuid4()), "geometry": []}]},
    ],
)
def test_playlist_bounds(payload):
    with pytest.raises(ValueError):
        validate_payload("ops_playlist", payload)


async def test_playlist_area_must_share_scope_and_be_readable(client, container, user, admin):
    claims = await claims_for(client, container, user)
    team = await team_for(container, admin, user)
    own_area = await seed_area(container, user.id, None, "Mine")
    team_area = await seed_area(container, user.id, team.id)
    hidden_area = await seed_area(container, admin.id, None, "Not yours")
    team_view = await make(container, claims, team_id=team.id)
    await make(container, claims, "ops_playlist", playlist(entry("area", own_area)))
    await make(
        container,
        claims,
        "ops_playlist",
        playlist(entry("area", team_area), entry("view", team_view.id)),
        team_id=team.id,
    )
    with pytest.raises(InvalidRequest, match="scope"):
        await make(container, claims, "ops_playlist", playlist(entry("area", team_area)))
    with pytest.raises(NotFound):
        await make(container, claims, "ops_playlist", playlist(entry("area", hidden_area)))
    with pytest.raises(NotFound):
        await make(container, claims, payload={**VIEW, "plan_id": str(uuid4())})
    administrator = await claims_for(client, container, admin)
    with pytest.raises(InvalidRequest, match="scope"):
        await make(container, administrator, "ops_playlist", playlist(entry("area", own_area)))


async def test_linked_plan_must_share_scope(client, container, user, admin):
    claims = await claims_for(client, container, user)
    team = await team_for(container, admin, user)
    plans = []
    for team_id in (None, team.id):
        plan = CollectionPlan(
            uuid4(), "Baltic", "", None, ("EE",), (), True, user.id, NOW, NOW, team_id
        )
        async with container.session_factory() as session:
            await container.repositories(session).plans.add(plan)
            await session.commit()
        plans.append(plan.id)
    await make(container, claims, payload={**VIEW, "plan_id": str(plans[0])})
    await make(container, claims, payload={**VIEW, "plan_id": str(plans[1])}, team_id=team.id)
    with pytest.raises(InvalidRequest, match="scope"):
        await make(container, claims, payload={**VIEW, "plan_id": str(plans[1])})
    with pytest.raises(NotFound):
        await make(container, claims, payload={**VIEW, "plan_id": str(uuid4())})


async def test_team_views_follow_current_membership_and_archive(client, container, user, admin):
    claims = await claims_for(client, container, user)
    team = await team_for(container, admin, user)
    view = await make(container, claims, team_id=team.id)
    async with container.session_factory() as session:
        await SqlTeamRepository(session).save(replace(team, is_active=False))
        await session.commit()
    async with container.session_factory() as session:
        service = container.map_workspace(session)
        assert (await service.get(claims, view.id)).id == view.id
        with pytest.raises(Forbidden):
            await service.update(claims, view.id, "Archived", VIEW, 1, CONTEXT)
    async with container.session_factory() as session:
        await SqlTeamRepository(session).remove_membership(team.id, user.id)
        await session.commit()
    async with container.session_factory() as session:
        service = container.map_workspace(session)
        assert await service.list(claims, "live_view") == []
        with pytest.raises(NotFound):
            await service.get(claims, view.id)


async def test_stale_link_for_another_user_is_not_found(client, container, user, admin):
    administrator = await claims_for(client, container, admin)
    private = await make(container, administrator)
    token = await login_token(client, user.email, USER_PASSWORD)
    response = await client.get(
        f"/api/map/workspaces/{private.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


async def test_playlist_entries_must_be_readable_views_or_areas_in_scope(
    client, container, user, admin
):
    claims = await claims_for(client, container, user)
    team = await team_for(container, admin, user)
    view = await make(container, claims)
    area = await seed_area(container, user.id, None, "Mine")
    drawings = await make(
        container, claims, "drawings", {"version": 1, "objects": [], "selectedId": None}
    )
    team_view = await make(container, claims, team_id=team.id)
    other = await make(container, await claims_for(client, container, admin))
    saved = await make(
        container, claims, "ops_playlist", playlist(entry("view", view.id), entry("area", area))
    )
    assert saved.kind == "ops_playlist"
    with pytest.raises(InvalidRequest, match="live view"):
        await make(container, claims, "ops_playlist", playlist(entry("view", drawings.id)))
    with pytest.raises(InvalidRequest, match="scope"):
        await make(container, claims, "ops_playlist", playlist(entry("view", team_view.id)))
    with pytest.raises(NotFound):
        await make(container, claims, "ops_playlist", playlist(entry("view", other.id)))
    with pytest.raises(NotFound):
        await make(container, claims, "ops_playlist", playlist(entry("area", uuid4())))


async def test_live_views_have_their_own_quota(client, container, user, monkeypatch):
    claims = await claims_for(client, container, user)
    monkeypatch.setattr(module, "MAX_SCOPE_DOCUMENTS", 1)
    await make(container, claims, "drawings", {"version": 1, "objects": [], "selectedId": None})
    await make(container, claims)
    monkeypatch.setattr(module, "MAX_LIVE_VIEWS", 1)
    with pytest.raises(InvalidRequest, match="limit"):
        await make(container, claims)


async def test_revoked_session_cannot_open_a_view(client, container, user):
    claims = await claims_for(client, container, user)
    view = await make(container, claims)
    async with container.session_factory() as session:
        await container.repositories(session).refresh_tokens.revoke_family(
            claims.family_id, container.clock.now()
        )
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(Unauthenticated):
            await container.map_workspace(session).get(claims, view.id)
