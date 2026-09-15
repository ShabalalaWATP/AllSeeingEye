"""Calendar recurrence, bounded saved scope and permission-preserving pause/resume."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.application.schedules.manage import ScheduleInput, build_schedule
from ase.application.schedules.report_request import scheduled_report_request
from ase.container import Container
from ase.domain.errors import InvalidRequest
from ase.domain.research import ResearchMode
from ase.domain.research_changes import ResearchChange
from ase.domain.schedules import next_run_after
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token

NOW = datetime(2026, 1, 31, 6, tzinfo=UTC)
BODY = {
    "name": "Monthly regional research",
    "template_id": "ask",
    "question": "What changed in energy policy?",
    "research_mode": "detailed",
    "country_isos": ["ua", "pl"],
    "research_web_search": True,
    "research_source_ids": ["rss-bbc-world"],
    "cadence": "monthly",
    "monthday": 31,
    "window_hours": 730 * 24,
}


@pytest.mark.parametrize("year,day", [(2026, 28), (2028, 29)])
def test_monthly_short_month_clamps_without_drifting(year: int, day: int) -> None:
    january = datetime(year, 1, 31, 6, tzinfo=UTC)
    february = next_run_after(january, 6, "monthly", monthday=31)
    assert february == datetime(year, 2, day, 6, tzinfo=UTC)
    assert next_run_after(february, 6, "monthly", monthday=31) == datetime(
        year, 3, 31, 6, tzinfo=UTC
    )


def test_monthly_before_run_and_december_rollover() -> None:
    before = datetime(2026, 12, 31, 5, 59, tzinfo=UTC)
    run = next_run_after(before, 6, "monthly", monthday=31)
    assert run == datetime(2026, 12, 31, 6, tzinfo=UTC)
    assert next_run_after(run, 6, "monthly", monthday=31) == datetime(2027, 1, 31, 6, tzinfo=UTC)
    local = datetime(2026, 1, 31, 7, tzinfo=timezone(timedelta(hours=2)))
    assert next_run_after(local, 6, "monthly", monthday=31) == NOW


@pytest.mark.parametrize(
    "changes",
    [
        {"monthday": 0},
        {"monthday": 32},
        {"window_hours": 17521},
        {"country_isos": ("ZZ",)},
        {"country_isos": ("UA",), "country_iso": "GB"},
        {"research_source_ids": ("",)},
        {"research_source_ids": ("source", "source")},
        {"research_mode": None, "research_web_search": True},
    ],
)
def test_schedule_rejects_invalid_additive_scope(changes: dict[str, object]) -> None:
    data = ScheduleInput(
        name="Recurring", template_id="ask", question="Question?", research_mode=ResearchMode.QUICK
    )
    with pytest.raises(InvalidRequest):
        build_schedule(
            replace(data, **changes), schedule_id=uuid4(), owner=uuid4(), created=NOW, now=NOW
        )


async def test_monthly_scope_round_trip_reaches_report_and_pause_keeps_configuration(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post("/api/schedules", json=BODY, headers=bearer(token))
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["country_isos"] == ["UA", "PL"] and item["country_iso"] is None
    assert item["monthday"] == 31 and item["research_web_search"] is True
    url = f"/api/schedules/{item['id']}"
    await create_user(container, email="other@example.com", password="another-long-passphrase")
    other = await login_token(client, "other@example.com", "another-long-passphrase")
    assert (
        await client.put(url, json={**BODY, "enabled": False}, headers=bearer(other))
    ).status_code == 404
    for enabled in (False, True):
        updated = await client.put(url, json={**BODY, "enabled": enabled}, headers=bearer(token))
        assert updated.status_code == 200
        assert updated.json()["enabled"] is enabled
        assert updated.json()["country_isos"] == ["UA", "PL"]
        assert updated.json()["research_source_ids"] == BODY["research_source_ids"]
    async with container.session_factory() as session:
        schedule = (await container.list_schedules(session).execute(user))[0]
    request = scheduled_report_request(schedule)
    assert request.country_isos == ("UA", "PL")
    assert request.research_web_search is True
    assert request.research_source_ids == ("rss-bbc-world",)
    assert request.window_hours == 730 * 24


async def test_nation_product_does_not_silently_widen_to_multiple_countries(
    client: AsyncClient, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post(
        "/api/schedules", json={**BODY, "template_id": "country_brief"}, headers=bearer(token)
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "changes",
    [
        {"country_isos": ("UA", "PL")},
        {"research_web_search": True},
        {"research_source_ids": ("source",)},
        {"window_hours": 720},
    ],
)
def test_scope_changes_reset_comparison_but_pause_preserves_it(changes: dict[str, object]) -> None:
    data = ScheduleInput(
        name="Recurring",
        template_id="ask",
        question="Question?",
        research_mode=ResearchMode.QUICK,
        country_isos=("UA",),
    )
    options = {"schedule_id": uuid4(), "owner": uuid4(), "created": NOW, "now": NOW}
    original = build_schedule(data, **options)
    original = replace(original, last_change=ResearchChange("baseline", uuid4(), uuid4()))
    paused = build_schedule(replace(data, enabled=False), previous=original, **options)
    assert paused.last_change == original.last_change
    changed = build_schedule(replace(data, **changes), previous=original, **options)
    assert changed.last_change is None


def test_next_slot_keeps_original_requested_month_day() -> None:
    february = datetime(2026, 2, 28, 6, tzinfo=UTC)
    assert next_run_after(february, 6, "monthly", monthday=31) == datetime(
        2026, 3, 31, 6, tzinfo=UTC
    )
