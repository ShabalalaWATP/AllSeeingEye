"""The tracker products: a conflict assessment scoped by a curated conflict, a SITREP by hazard."""

from __future__ import annotations

import json

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, good_body
from tracker_helpers import conflict_events, disaster_events


async def test_conflict_assessment_and_disaster_sitrep_scope_the_evidence(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await seed_legacy_profile(container, PROFILE)
    now = container.clock.now()
    container.store.upsert([*conflict_events(now), *disaster_events(now)])

    templates = await client.get("/api/reports/templates", headers=bearer(token))
    flags = {t["id"]: (t["needs_conflict"], t["needs_hazard"]) for t in templates.json()["items"]}
    assert flags["conflict_assessment"] == (True, False)
    assert flags["disaster_sitrep"] == (False, True)
    assert flags["intsum"] == (False, False)

    judgements = good_body()["key_judgements"]
    fits = good_body(
        key_judgements=[judgements[0], {**judgements[1], "supporting_evidence": ["E2"]}]
    )
    gateway = ScriptedGateway(json.dumps(fits))
    container.llm = gateway
    created = await client.post(
        "/api/reports",
        json={"template": "conflict_assessment", "conflict": "Ukraine"},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    report = created.json()["report"]
    assert report["title"] == "Conflict assessment: Russia's war in Ukraine"
    assert report["scope"]["conflict"] == "ukraine" and report["scope"]["window_hours"] == 168
    titles = [item["title"] for item in created.json()["version"]["evidence"]]
    assert "Shelling in Kharkiv" in titles and "Talks in Kyiv" in titles
    assert "Clash in Sudan" not in titles
    assert titles[0] == "Shelling in Kharkiv"  # keyword match ranks first
    prompt = gateway.requests[0].messages[1].content
    assert (
        "Background from the curated tracker" in prompt
        and "Belligerents: Russia, Ukraine" in prompt
    )
    assert "Product: Conflict assessment." in gateway.requests[0].messages[0].content

    container.llm = ScriptedGateway(json.dumps(fits))
    sitrep = await client.post(
        "/api/reports",
        json={"template": "disaster_sitrep", "hazard": "earthquake"},
        headers=bearer(token),
    )
    assert sitrep.status_code == 201, sitrep.text
    assert sitrep.json()["report"]["title"] == "Disaster SITREP: earthquakes"
    assert sitrep.json()["report"]["scope"]["hazard"] == "earthquake"
    # Only the earthquake inside the 72-hour window; the cyclone and volcano are other hazards.
    assert [item["title"] for item in sitrep.json()["version"]["evidence"]] == ["M6.1 quake"]

    unknown = await client.post(
        "/api/reports",
        json={"template": "conflict_assessment", "conflict": "atlantis"},
        headers=bearer(token),
    )
    assert unknown.status_code == 422 and "conflict" in unknown.json()["error"]["message"]
    assert (
        await client.post(
            "/api/reports",
            json={"template": "disaster_sitrep", "hazard": "plague"},
            headers=bearer(token),
        )
    ).status_code == 422
