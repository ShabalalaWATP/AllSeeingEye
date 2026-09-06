"""Scheduled products: next-run arithmetic, ownership through the API, and the runner."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient

from ase.adapters.persistence.schedules import SqlScheduleStore
from ase.application.schedules.runner import ScheduleRunner
from ase.container import Container
from ase.domain.schedules import Schedule, next_run_after
from ase.domain.users import User
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

FRIDAY = datetime(2026, 9, 4, 7, tzinfo=UTC)


def test_next_run_follows_the_cadence() -> None:
    assert next_run_after(FRIDAY, 6, "daily") == datetime(2026, 9, 5, 6, tzinfo=UTC)
    assert next_run_after(FRIDAY, 9, "daily") == datetime(2026, 9, 4, 9, tzinfo=UTC)
    assert next_run_after(FRIDAY, 6, "weekdays") == datetime(2026, 9, 7, 6, tzinfo=UTC)
    assert next_run_after(FRIDAY, 6, "weekly", weekday=0) == datetime(2026, 9, 7, 6, tzinfo=UTC)
    assert next_run_after(FRIDAY, 6, "weekly", weekday=4) == datetime(2026, 9, 11, 6, tzinfo=UTC)


async def test_schedules_are_validated_and_owned(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    body = {"name": "Morning INTSUM", "template_id": "intsum", "country_iso": "ua", "hour_utc": 6}
    for bad in (
        {**body, "template_id": "nope"},
        {**body, "template_id": "conflict_assessment"},
        {**body, "template_id": "ask"},
        {**body, "template_id": "country_brief", "country_iso": None},
        {**body, "cadence": "hourly"},
        {**body, "plan_id": str(uuid4())},
    ):
        response = await client.post("/api/schedules", json=bad, headers=bearer(token))
        assert response.status_code == 422, bad
    created = await client.post("/api/schedules", json=body, headers=bearer(token))
    assert created.status_code == 201, created.text
    assert created.json()["country_iso"] == "UA"
    expected = next_run_after(container.clock.now(), 6, "daily")
    assert datetime.fromisoformat(created.json()["next_run_at"]) == expected
    schedule_id = created.json()["id"]

    await create_user(container, email="second@example.com", password="another-long-passphrase")
    second = await login_token(client, "second@example.com", "another-long-passphrase")
    forbidden = await client.put(f"/api/schedules/{schedule_id}", json=body, headers=bearer(second))
    assert forbidden.status_code == 404
    edited = await client.put(
        f"/api/schedules/{schedule_id}",
        json={**body, "cadence": "weekly", "weekday": 0, "enabled": False},
        headers=bearer(admin_token),
    )
    assert edited.status_code == 200 and edited.json()["cadence"] == "weekly"
    assert edited.json()["created_by"] == created.json()["created_by"]
    listed = await client.get("/api/schedules", headers=bearer(second))
    assert listed.json()["items"] == []
    assert (
        await client.delete(f"/api/schedules/{uuid4()}", headers=bearer(token))
    ).status_code == 404
    assert (
        await client.delete(f"/api/schedules/{schedule_id}", headers=bearer(token))
    ).status_code == 204


async def test_runner_produces_due_reports_and_records_failures(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await client.post(
        "/api/admin/llm/profiles",
        json={**PROFILE, "roles": ["assessment"]},
        headers=bearer(admin_token),
    )
    hour = (container.clock.now().hour + 1) % 24
    body = {
        "name": "Morning INTSUM", "template_id": "intsum", "country_iso": "UA",
        "hour_utc": hour, "window_hours": 336,
    }  # fmt: skip
    created = await client.post("/api/schedules", json=body, headers=bearer(token))
    assert created.status_code == 201, created.text
    container.store.upsert(conflict_events(container.clock.now()))
    container.llm = ScriptedGateway(json.dumps(good_body()))
    store = SqlScheduleStore(container.session_factory, container.access_policy)
    runner = ScheduleRunner(store, container.schedule_report, container.clock)
    assert await runner.run_once() == []  # not due yet

    container.clock.advance(timedelta(hours=2))
    ran = await runner.run_once()
    assert [item.name for item in ran] == ["Morning INTSUM"]
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    listed = await client.get("/api/schedules", headers=bearer(token))
    item = listed.json()["items"][0]
    assert item["last_report_id"] is not None and item["last_error"] is None
    assert datetime.fromisoformat(item["next_run_at"]) > container.clock.now()
    report = await client.get(f"/api/reports/{item['last_report_id']}", headers=bearer(token))
    assert report.status_code == 200 and report.json()["report"]["scope"]["country"] == "UA"
    assert await runner.run_once() == []  # booked for tomorrow

    async def failing(schedule: Schedule) -> object:
        raise RuntimeError("boom")

    container.clock.advance(timedelta(days=1))
    broken = ScheduleRunner(store, failing, container.clock)  # type: ignore[arg-type]
    assert len(await broken.run_once()) == 1
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    listed = await client.get("/api/schedules", headers=bearer(token))
    assert listed.json()["items"][0]["last_error"] == "RuntimeError: boom"
