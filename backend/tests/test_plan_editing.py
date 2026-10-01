"""Editing a collection plan keeps its identity and scope and refuses stale revisions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from direction_scope_helpers import DirectionActors, area, direction_actors, plan


@pytest.fixture
async def actors(
    client: AsyncClient, container: Container, admin: User, user: User
) -> DirectionActors:
    return await direction_actors(client, container, user)


def two_pirs(name: str = "Edited", team: str | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "team_id": team,
        "countries": ["ua", "pl"],
        "pirs": [
            {
                "text": "Will the border close?",
                "sirs": [
                    {"text": "Crossing closures", "keywords": ["closure"]},
                    {"text": "Queue reports", "categories": ["news"]},
                ],
            },
            {"text": "Are reinforcements arriving?", "sirs": [{"text": "Convoys"}]},
        ],
    }


async def _create(client: AsyncClient, headers: dict[str, str], **kwargs: Any) -> dict[str, Any]:
    response = await client.post("/api/direction/plans", json=plan(**kwargs), headers=headers)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_edit_keeps_identity_owner_and_scope_with_several_requirements(
    client: AsyncClient, actors: DirectionActors
) -> None:
    created = await _create(client, actors.owner, team=actors.team)
    edited = await client.put(
        f"/api/direction/plans/{created['id']}",
        json={**two_pirs(team=actors.team), "expected_updated_at": created["updated_at"]},
        headers=actors.owner,
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["id"] == created["id"]
    assert body["created_by"] == created["created_by"]
    assert body["created_at"] == created["created_at"]
    assert body["team_id"] == actors.team
    assert body["updated_at"] != created["updated_at"]
    assert [pir["code"] for pir in body["pirs"]] == ["PIR-1", "PIR-2"]
    assert [sir["code"] for sir in body["pirs"][0]["sirs"]] == ["SIR-1.1", "SIR-1.2"]
    assert body["pirs"][1]["sirs"][0]["code"] == "SIR-2.1"
    assert body["countries"] == ["UA", "PL"]
    listed = await client.get("/api/direction/plans", headers=actors.owner)
    assert [item["id"] for item in listed.json()["items"]] == [created["id"]]

    # A second edit from the fresh revision succeeds even when the clock has not moved.
    removed = two_pirs("Shorter", actors.team)
    removed["pirs"] = removed["pirs"][1:]
    again = await client.put(
        f"/api/direction/plans/{created['id']}",
        json={**removed, "expected_updated_at": body["updated_at"]},
        headers=actors.owner,
    )
    assert again.status_code == 200, again.text
    # Positional codes renumber when an earlier requirement is removed.
    assert again.json()["pirs"][0]["code"] == "PIR-1"
    assert again.json()["pirs"][0]["sirs"][0] == {
        "code": "SIR-1.1",
        "text": "Convoys",
        "keywords": [],
        "categories": [],
    }
    later = datetime.fromisoformat(again.json()["updated_at"])
    assert later > datetime.fromisoformat(body["updated_at"])


async def test_a_stale_revision_is_refused_and_leaves_the_plan_unchanged(
    client: AsyncClient, actors: DirectionActors
) -> None:
    created = await _create(client, actors.owner)
    first = await client.put(
        f"/api/direction/plans/{created['id']}",
        json={**two_pirs("First"), "expected_updated_at": created["updated_at"]},
        headers=actors.owner,
    )
    assert first.status_code == 200, first.text
    stale = await client.put(
        f"/api/direction/plans/{created['id']}",
        json={**two_pirs("Second"), "expected_updated_at": created["updated_at"]},
        headers=actors.owner,
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] == "conflict"
    current = await client.get(f"/api/direction/plans/{created['id']}", headers=actors.owner)
    assert current.json()["plan"]["name"] == "First"
    assert current.json()["plan"]["updated_at"] == first.json()["updated_at"]


async def test_updates_need_a_revision_and_share_creation_validation(
    client: AsyncClient, actors: DirectionActors
) -> None:
    created = await _create(client, actors.owner, team=actors.team)
    route = f"/api/direction/plans/{created['id']}"
    revision = {"expected_updated_at": created["updated_at"]}
    missing = await client.put(route, json=two_pirs(team=actors.team), headers=actors.owner)
    assert missing.status_code == 422
    empty_pir = two_pirs(team=actors.team)
    empty_pir["pirs"][0]["text"] = ""
    assert (
        await client.put(route, json={**empty_pir, **revision}, headers=actors.owner)
    ).status_code == 422
    blank_sir = two_pirs(team=actors.team)
    blank_sir["pirs"][1]["sirs"][0]["text"] = "   "
    blank = await client.put(route, json={**blank_sir, **revision}, headers=actors.owner)
    assert blank.status_code == 422
    assert "specific intelligence requirement" in blank.json()["error"]["message"]
    personal_area = await client.post("/api/direction/aois", json=area(), headers=actors.owner)
    mismatched = {**two_pirs(team=actors.team), "aoi_id": personal_area.json()["id"]}
    assert (
        await client.put(route, json={**mismatched, **revision}, headers=actors.owner)
    ).status_code == 422
    rescoped = await client.put(route, json={**two_pirs(), **revision}, headers=actors.owner)
    assert rescoped.status_code == 422
    unchanged = await client.get(route, headers=actors.owner)
    assert unchanged.json()["plan"]["updated_at"] == created["updated_at"]


async def test_archived_or_inaccessible_plans_cannot_be_edited(
    client: AsyncClient, actors: DirectionActors
) -> None:
    created = await _create(client, actors.owner, team=actors.team)
    route = f"/api/direction/plans/{created['id']}"
    body = {**two_pirs(team=actors.team), "expected_updated_at": created["updated_at"]}
    assert (await client.put(route, json=body, headers=actors.outsider)).status_code == 404
    assert (await client.put(route, json=body, headers=actors.member)).status_code == 403
    assert (
        await client.patch(
            f"/api/teams/{actors.team}", json={"is_active": False}, headers=actors.admin
        )
    ).status_code == 200
    assert (await client.put(route, json=body, headers=actors.owner)).status_code == 403
    assert (await client.get(route, headers=actors.owner)).json()["plan"]["name"] == "Plan"


async def test_plan_definition_reads_are_scoped_and_lightweight(
    client: AsyncClient, actors: DirectionActors
) -> None:
    created = await _create(client, actors.owner, team=actors.team)
    route = f"/api/direction/plans/{created['id']}/definition"
    read = await client.get(route, headers=actors.member)
    assert read.status_code == 200, read.text
    assert read.json() == created
    assert read.headers["cache-control"] == "private, no-store"
    assert (await client.get(route, headers=actors.outsider)).status_code == 404
