"""Scheduled products: next-run arithmetic, ownership through the API, and the runner."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from httpx import AsyncClient

from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.container import Container
from ase.domain.schedules import next_run_after
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
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE

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
    # New subscriptions default to weekly, the cheapest useful recurring shape.
    assert created.json()["cadence"] == "weekly"
    expected = next_run_after(container.clock.now(), 6, "weekly")
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


async def test_runner_enqueues_due_slot_once_without_inline_production(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    hour = (container.clock.now().hour + 1) % 24
    body = {
        "name": "Morning INTSUM", "template_id": "intsum", "country_iso": "UA",
        "hour_utc": hour, "window_hours": 336, "cadence": "daily",
    }  # fmt: skip
    created = await client.post("/api/schedules", json=body, headers=bearer(token))
    assert created.status_code == 201, created.text
    runner = container.schedule_runner
    assert await runner.run_once() == 0  # not due yet

    container.clock.advance(timedelta(hours=2))
    assert await runner.run_once() == 1
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    listed = await client.get("/api/schedules", headers=bearer(token))
    item = listed.json()["items"][0]
    assert item["last_report_id"] is None and item["last_error"] is None
    assert datetime.fromisoformat(item["next_run_at"]) > container.clock.now()
    async with container.session_factory() as session:
        edition = await SqlSubscriptionEditionRepository(session).active(UUID(item["id"]))
        assert edition is not None and edition.job_id is not None
    assert await runner.run_once() == 0
