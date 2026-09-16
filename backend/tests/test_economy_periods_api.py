"""Real economy endpoints freeze selected intervals and reject unsupported windows."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from ase.domain.economy_periods import EconomyWindowDays
from ase.domain.events import Category
from feeds_helpers import make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_job_api_helpers import job_settings, prepared, stored
from test_economy_briefing_api import macro_fixture

__all__ = ["job_settings"]


@pytest.mark.parametrize("days", EconomyWindowDays)
async def test_duration_and_reported_period_match_durable_work_after_reuse(
    client, user, container, monkeypatch, days
):
    gateway, headers = await prepared(container, client)
    now = container.clock.now()
    snapshot = AsyncMock(return_value=macro_fixture(now))
    monkeypatch.setattr(container.economy, "snapshot", snapshot)
    response = await client.post(f"/api/economy/briefing?days={int(days)}", headers=headers)
    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["window_days"] == int(days)
    assert datetime.fromisoformat(payload["period_from"]) == now - timedelta(days=days)
    assert datetime.fromisoformat(payload["period_to"]) == now
    assert datetime.fromisoformat(payload["next_refresh_at"]) == now + timedelta(hours=24)
    frozen = (await stored(container, payload["job"]["id"])).payload["input"]
    assert frozen["scope"]["window_hours"] == int(days) * 24
    assert datetime.fromisoformat(frozen["period_from"]) == now - timedelta(days=days)
    assert datetime.fromisoformat(frozen["period_to"]) == now
    assert "period_from" not in payload["job"]  # Generic progress contract is unchanged.
    container.clock.advance(timedelta(minutes=5))
    again = await client.post(f"/api/economy/briefing?days={int(days)}", headers=headers)
    assert again.status_code == 202, again.text
    assert again.json()["job"]["id"] == payload["job"]["id"]
    for field in ("period_from", "period_to", "window_days", "next_refresh_at"):
        assert again.json()[field] == payload[field]
    assert snapshot.await_count == 1 and not gateway.calls


async def test_switching_window_uses_a_distinct_report_and_default_is_two_days(
    client, user, container, monkeypatch
):
    _, headers = await prepared(container, client)
    monkeypatch.setattr(
        container.economy, "snapshot", AsyncMock(return_value=macro_fixture(container.clock.now()))
    )
    first = await client.post("/api/economy/briefing", headers=headers)
    longer = await client.post("/api/economy/briefing?days=14", headers=headers)
    again = await client.post("/api/economy/briefing?days=2", headers=headers)
    assert first.status_code == longer.status_code == again.status_code == 202
    assert first.json()["window_days"] == 2 and longer.json()["window_days"] == 14
    assert first.json()["job"]["id"] != longer.json()["job"]["id"]
    assert first.json()["job"]["id"] == again.json()["job"]["id"]


async def test_both_endpoints_reject_unsupported_windows_without_preparing_work(
    client, user, container, monkeypatch
):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    snapshot = AsyncMock()
    monkeypatch.setattr(container.economy, "snapshot", snapshot)
    for value in ("1", "3", "6", "15", "365", "true", "tomorrow"):
        news = await client.get(f"/api/economy/news?days={value}", headers=headers)
        report = await client.post(f"/api/economy/briefing?days={value}", headers=headers)
        assert news.status_code == report.status_code == 422
    snapshot.assert_not_awaited()


async def test_headline_api_filters_each_actual_publication_period(client, user, container):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    now = container.clock.now()
    container.store.upsert(
        tuple(
            make_event(
                str(day),
                source_id="economic_bbc_business",
                category=Category.ECONOMIC,
                title=f"Inflation and interest rates report {day} days ago",
                published_at=now - timedelta(days=day),
                observed_at=now,
            )
            for day in (1, 4, 6, 13)
        )
    )
    for days, count in zip(EconomyWindowDays, (1, 2, 3, 4), strict=True):
        result = await client.get(f"/api/economy/news?days={int(days)}", headers=headers)
        assert result.status_code == 200, result.text
        payload = result.json()
        assert payload["window_hours"] == int(days) * 24
        assert datetime.fromisoformat(payload["as_of"]) == now
        assert len(payload["items"]) == count
