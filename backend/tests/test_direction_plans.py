"""Direction: areas of interest, collection plans, their evidence and plan-scoped reports."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from httpx import AsyncClient

from ase.container import Container
from ase.domain.collection import (
    AreaOfInterest,
    CollectionPlan,
    Sir,
    in_scope,
    numbered,
    plan_matches,
    sir_matches,
)
from ase.domain.events import BoundingBox, Category, Point
from ase.domain.users import User
from feeds_helpers import make_event
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    bearer,
    create_user,
    login_token,
)
from report_helpers import PROFILE, ScriptedGateway, good_body
from tracker_helpers import conflict_events

PLAN = {
    "name": "Kharkiv axis",
    "description": "What is the Russian intent on the Kharkiv axis this month?",
    "countries": ["ua"],
    "pirs": [
        {
            "text": "Will Russia mount a new offensive towards Kharkiv?",
            "sirs": [
                {
                    "text": "Strikes and shelling around Kharkiv",
                    "keywords": ["Kharkiv", "shelling"],
                },
                {"text": "Talks or ceasefire moves", "keywords": ["talks"], "categories": ["news"]},
                {"text": "Any conflict event", "categories": ["conflict"]},
            ],
        }
    ],
}


def test_domain_matching_and_numbering() -> None:
    pirs = numbered(
        [
            (
                "Will Russia mount a new offensive?",
                [
                    ("Shelling around Kharkiv", ["Kharkiv", " shelling "], [Category.CONFLICT]),
                    ("", [], []),
                ],
            ),
            ("   ", []),
        ]
    )
    assert [pir.code for pir in pirs] == ["PIR-1"]
    assert [sir.code for sir in pirs[0].sirs] == ["SIR-1.1"]
    assert pirs[0].sirs[0].keywords == ("Kharkiv", "shelling")
    shelling = make_event(
        "s",
        category=Category.CONFLICT,
        title="Shelling in Kharkiv",
        point=Point(36.2, 49.9),
        country_iso="UA",
    )
    talks = make_event(
        "t", category=Category.NEWS, title="Talks in Kyiv", point=None, country_iso="UA"
    )
    sir = pirs[0].sirs[0]
    assert sir_matches(sir, shelling) and not sir_matches(sir, talks)
    assert sir_matches(Sir("SIR-x", "any conflict", categories=(Category.CONFLICT,)), shelling)
    assert not sir_matches(Sir("SIR-y", "nothing to match on"), shelling)
    now = datetime(2026, 9, 5, tzinfo=UTC)
    plan = CollectionPlan(uuid4(), "p", "", None, ("UA",), pirs, True, uuid4(), now, now)
    assert plan_matches(plan, shelling) == ("SIR-1.1",)
    assert plan.search_terms() == ("Kharkiv", "shelling")
    assert plan.direction().pir.startswith("Will Russia") and plan.direction().categories == (
        Category.CONFLICT,
    )
    box = AreaOfInterest(uuid4(), "box", "bbox", BoundingBox(30, 44, 41, 53), (), uuid4(), now)
    nations = AreaOfInterest(uuid4(), "ua", "countries", None, ("UA",), uuid4(), now)
    assert box.contains(shelling) and not box.contains(talks)
    assert nations.contains(talks) and in_scope(plan, None, talks) and in_scope(plan, box, shelling)
    sudan = make_event(
        "x", category=Category.CONFLICT, title="Clash", point=Point(32.5, 15.6), country_iso="SD"
    )
    assert not in_scope(plan, None, sudan) and not in_scope(plan, box, sudan)


async def test_areas_and_plans_are_owned_and_scoped(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    bad = await client.post(
        "/api/direction/aois", json={"name": "x", "kind": "bbox"}, headers=bearer(token)
    )
    assert bad.status_code == 422
    created = await client.post(
        "/api/direction/aois",
        json={"name": "Eastern Ukraine", "kind": "bbox", "bbox": [30, 44, 41, 53]},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    aoi_id = created.json()["id"]
    listed = await client.get("/api/direction/aois", headers=bearer(admin_token))
    assert [area["name"] for area in listed.json()["items"]] == ["Eastern Ukraine"]

    plan = await client.post(
        "/api/direction/plans", json={**PLAN, "aoi_id": aoi_id}, headers=bearer(token)
    )
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["id"]
    assert plan.json()["pirs"][0]["sirs"][0]["code"] == "SIR-1.1"
    assert plan.json()["countries"] == ["UA"]
    unknown_area = await client.post(
        "/api/direction/plans", json={**PLAN, "aoi_id": str(uuid4())}, headers=bearer(token)
    )
    assert unknown_area.status_code == 422

    container.store.upsert(conflict_events(container.clock.now()))
    evidence = await client.get(f"/api/direction/plans/{plan_id}", headers=bearer(admin_token))
    assert evidence.status_code == 200, evidence.text
    sirs = {sir["code"]: [e["title"] for e in sir["events"]] for sir in evidence.json()["sirs"]}
    assert sirs["SIR-1.1"] == ["Shelling in Kharkiv"]
    assert sirs["SIR-1.2"] == []  # the talks item has no point, so the box excludes it
    # The clash from ten days ago sits outside the seven-day evidence window.
    assert set(sirs["SIR-1.3"]) == {"Shelling in Kharkiv", "Drone strike near Sumy"}
    assert evidence.json()["aoi"]["name"] == "Eastern Ukraine"

    # Another user cannot edit or delete; the owner and an admin can.
    other = await client.put(
        f"/api/direction/plans/{plan_id}", json=PLAN, headers=bearer(admin_token)
    )
    assert other.status_code == 200  # admins may edit
    assert other.json()["created_by"] == plan.json()["created_by"]
    forbidden = await client.delete(f"/api/direction/aois/{aoi_id}", headers=bearer(admin_token))
    assert forbidden.status_code == 204  # admin may delete areas too
    assert (
        await client.get(f"/api/direction/plans/{uuid4()}", headers=bearer(token))
    ).status_code == 404
    assert (
        await client.delete(f"/api/direction/plans/{plan_id}", headers=bearer(token))
    ).status_code == 204
    assert (await client.get("/api/direction/plans", headers=bearer(token))).json()["items"] == []


async def test_a_second_user_cannot_change_someone_elses_plan(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    plan = await client.post("/api/direction/plans", json=PLAN, headers=bearer(token))
    plan_id = plan.json()["id"]
    await create_user(container, email="second@example.com", password="another-long-passphrase")
    second = await login_token(client, "second@example.com", "another-long-passphrase")
    assert (
        await client.put(f"/api/direction/plans/{plan_id}", json=PLAN, headers=bearer(second))
    ).status_code == 403
    assert (
        await client.delete(f"/api/direction/plans/{plan_id}", headers=bearer(second))
    ).status_code == 403
    readable = await client.get(f"/api/direction/plans/{plan_id}", headers=bearer(second))
    assert readable.status_code == 200


async def test_a_report_scoped_by_a_plan_skips_the_direction_call(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await client.post(
        "/api/admin/llm/profiles",
        json={**PROFILE, "roles": ["direction", "assessment"]},
        headers=bearer(admin_token),
    )
    plan = await client.post("/api/direction/plans", json=PLAN, headers=bearer(token))
    plan_id = plan.json()["id"]
    container.store.upsert(conflict_events(container.clock.now()))
    gateway = ScriptedGateway(json.dumps(good_body()))
    container.llm = gateway
    created = await client.post(
        "/api/reports", json={"template": "ask", "plan": plan_id}, headers=bearer(token)
    )
    assert created.status_code == 201, created.text
    assert [r.schema_name for r in gateway.requests] == ["report"]
    assert created.json()["report"]["title"] == "Ask the Eye: Kharkiv axis"
    assert created.json()["report"]["scope"]["plan"] == plan_id
    assert created.json()["report"]["scope"]["question"].startswith("Will Russia mount")
    version = created.json()["version"]
    assert version["direction"]["pir"].startswith("Will Russia mount")
    assert version["direction"]["search_terms"] == ["Kharkiv", "shelling", "talks"]
    assert version["evidence"][0]["title"] == "Shelling in Kharkiv"
    prompt = gateway.requests[0].messages[1].content
    assert "SIR-1: Strikes and shelling around Kharkiv" in prompt
    assert "Background from the curated tracker" in prompt  # the plan's description
    missing = await client.post(
        "/api/reports", json={"template": "ask", "plan": str(uuid4())}, headers=bearer(token)
    )
    assert missing.status_code == 422
