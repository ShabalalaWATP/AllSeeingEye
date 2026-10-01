"""Map matches for a collection plan: a bounded, scoped, on-demand sample of the live store."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from ase.container import Container
from ase.domain.events import Category, Point
from ase.domain.users import User
from direction_scope_helpers import DirectionActors, direction_actors
from feeds_helpers import make_event
from tracker_helpers import conflict_events

PLAN: dict[str, Any] = {
    "name": "Kharkiv axis",
    "countries": ["UA"],
    "pirs": [
        {
            "text": "Is an offensive coming?",
            "sirs": [
                {"text": "Shelling", "keywords": ["shelling"]},
                {"text": "Any conflict", "categories": ["conflict"]},
            ],
        }
    ],
}


@pytest.fixture
async def actors(
    client: AsyncClient, container: Container, admin: User, user: User
) -> DirectionActors:
    return await direction_actors(client, container, user)


async def _plan(client: AsyncClient, headers: dict[str, str], **changes: Any) -> dict[str, Any]:
    response = await client.post("/api/direction/plans", json={**PLAN, **changes}, headers=headers)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_matches_list_every_sir_code_per_event_with_limits(
    client: AsyncClient, container: Container, actors: DirectionActors
) -> None:
    plan = await _plan(client, actors.owner, team_id=actors.team)
    container.store.upsert(conflict_events(container.clock.now()))
    response = await client.get(
        f"/api/direction/plans/{plan['id']}/map-matches", headers=actors.member
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    body = response.json()
    assert body["plan"]["id"] == plan["id"]
    assert body["plan"]["updated_at"] == plan["updated_at"]
    assert body["window_hours"] == 168
    assert body["pool_limit"] == 5000
    assert body["per_requirement_limit"] == 30
    assert body["truncated"] is False
    by_title = {
        event["title"]: event["codes"]
        for event in body["matches"]
        for event in [{**event, "title": _title(container, event["event_id"])}]
    }
    assert by_title["Shelling in Kharkiv"] == ["SIR-1.1", "SIR-1.2"]
    assert by_title["Drone strike near Sumy"] == ["SIR-1.2"]
    assert "Last week's clash" not in by_title  # outside the seven-day window


def _title(container: Container, event_id: str) -> str:
    event = container.store.get(event_id)
    return event.title if event is not None else ""


async def test_a_capped_requirement_reports_truncation(
    client: AsyncClient, container: Container, actors: DirectionActors
) -> None:
    plan = await _plan(client, actors.owner)
    now = container.clock.now()
    container.store.upsert(
        [
            make_event(
                f"s{index}",
                source_id="gdelt",
                category=Category.CONFLICT,
                subtype="battle",
                title=f"Shelling {index}",
                point=Point(36.2, 49.9),
                country_iso="UA",
                published_at=now - timedelta(minutes=index),
            )
            for index in range(35)
        ]
    )
    response = await client.get(
        f"/api/direction/plans/{plan['id']}/map-matches", headers=actors.owner
    )
    body = response.json()
    assert body["truncated"] is True
    assert len(body["matches"]) == 30


async def test_unreadable_plans_are_not_disclosed(
    client: AsyncClient, container: Container, actors: DirectionActors
) -> None:
    personal = await _plan(client, actors.owner)
    team = await _plan(client, actors.admin, team_id=actors.other_team)
    for plan_id, headers in (
        (personal["id"], actors.member),
        (personal["id"], actors.outsider),
        (team["id"], actors.owner),
    ):
        response = await client.get(f"/api/direction/plans/{plan_id}/map-matches", headers=headers)
        assert response.status_code == 404, response.text
        assert "Kharkiv" not in response.text
