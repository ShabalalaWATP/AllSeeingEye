"""New subscriptions start weekly at Quick depth; existing ones keep what they have."""

from __future__ import annotations

from ase.api.schemas_schedules import ScheduleFromBriefIn, ScheduleIn
from ase.application.schedules.definition import ScheduleInput
from ase.domain.research import ResearchMode
from ase.domain.schedules import DEFAULT_CADENCE, DEFAULT_RESEARCH_MODE
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

BODY = {"name": "Kyiv watch", "template_id": "intsum", "country_iso": "UA", "hour_utc": 6}


def test_the_documented_defaults_are_weekly_and_quick() -> None:
    assert DEFAULT_CADENCE == "weekly"
    assert DEFAULT_RESEARCH_MODE is ResearchMode.QUICK


def test_every_creation_contract_defaults_to_the_weekly_cadence() -> None:
    assert ScheduleIn(name="A", template_id="intsum").cadence == DEFAULT_CADENCE
    assert ScheduleInput(name="A", template_id="intsum").cadence == DEFAULT_CADENCE
    from_brief = ScheduleFromBriefIn(
        brief_id="11111111-1111-1111-1111-111111111111", brief_revision=1
    )
    assert from_brief.cadence == DEFAULT_CADENCE


async def test_a_new_subscription_is_weekly_unless_asked_otherwise(client, user):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post("/api/schedules", json=BODY, headers=bearer(token))
    assert created.status_code == 201, created.text
    assert created.json()["cadence"] == "weekly"
    chosen = await client.post(
        "/api/schedules", json={**BODY, "name": "Daily", "cadence": "daily"}, headers=bearer(token)
    )
    assert chosen.status_code == 201 and chosen.json()["cadence"] == "daily"


async def test_an_existing_subscription_keeps_its_cadence_and_depth(client, user):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post(
        "/api/schedules",
        json={**BODY, "cadence": "daily", "hour_utc": 7},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    schedule_id = created.json()["id"]
    # An edit that does not mention the cadence must not silently move it to the default.
    edited = await client.put(
        f"/api/schedules/{schedule_id}",
        json={**BODY, "cadence": "daily", "hour_utc": 8},
        headers=bearer(token),
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["cadence"] == "daily"
    listed = await client.get("/api/schedules", headers=bearer(token))
    assert [item["cadence"] for item in listed.json()["items"]] == ["daily"]
