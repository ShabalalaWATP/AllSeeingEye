"""Coverage is authenticated and cannot disclose upstream credentials or diagnostics."""

from datetime import timedelta

import pytest

from ase.adapters.feeds.conflict_acled import AcledConnector
from ase.api.routers.conflict_coverage import screening_status
from ase.application.feeds.health import SourceStatus
from ase.domain.events import Category, Point
from feeds_helpers import make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_conflict_sources import Http, acled


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("disabled", "not_configured"),
        ("no_global_model", "not_configured"),
        ("model_error", "degraded"),
        ("unavailable", "degraded"),
        ("ready", "healthy"),
        ("budget_exhausted", "waiting"),
        ("waiting_for_source_text", "waiting"),
        ("model_changed", "waiting"),
        ("private upstream error", "waiting"),
    ],
)
def test_screening_status_uses_safe_public_descriptions(state, expected):
    result = screening_status(state)
    assert result.id == "conflict_screening" and result.status == expected
    assert "private upstream error" not in result.detail
    assert result.last_success is None


async def test_coverage_requires_login_and_shows_safe_provider_health(client, container, user):
    assert (await client.get("/api/trackers/conflict-sources")).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    health = container.health.get("gdelt_events")
    health.status = SourceStatus.DEGRADED
    health.last_error = "secret-token upstream-private-url"
    response = await client.get("/api/trackers/conflict-sources", headers=bearer(token))
    assert response.status_code == 200
    rows = {row["id"]: row for row in response.json()["items"]}
    assert rows["gdelt_events"]["status"] == "degraded"
    assert rows["ucdp_candidate"]["dataset_release"] == "26.0.7"
    assert rows["acled_events"]["status"] == "not_configured"
    assert rows["reliefweb_reports"]["status"] == "not_configured"
    assert rows["conflict_screening"]["status"] == "waiting"
    assert "secret-token" not in response.text and "upstream-private-url" not in response.text
    health.status = SourceStatus.HEALTHY
    response = await client.get("/api/trackers/conflict-sources", headers=bearer(token))
    assert (
        next(row for row in response.json()["items"] if row["id"] == "gdelt_events")["status"]
        == "healthy"
    )


async def test_monthly_baseline_is_evidence_without_recent_activity(client, container, user):

    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    now = container.clock.now()
    event = make_event(
        "baseline",
        category=Category.CONFLICT,
        subtype="organised_violence",
        source_id="ucdp_candidate",
        point=Point(36.2, 49.9),
        country_iso="UA",
    ).with_changes(
        published_at=None,
        observed_at=now,
        attributes={
            "occurrence_start": (now - timedelta(days=40)).isoformat(),
            "dataset_status": "provisional_monthly",
        },
    )
    container.store.upsert([event])
    response = await client.get("/api/trackers/conflicts/ukraine", headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert body["card"]["activity"]["last_7d"] == 0
    assert body["card"]["fatalities_7d"] is None
    assert [event["id"] for event in body["events"]] == [event.id]
    assert body["evidence_groups"][0]["report_count"] == 1


async def test_acled_occurrence_is_counted_without_publication_and_outside_points_excluded(
    container,
):
    now = container.clock.now()
    http = Http({"status": 200, "data": [acled(event_date=now.date().isoformat(), fatalities="4")]})
    events = await AcledConnector(http, container.clock, "fixture-token").fetch()
    assert events[0].published_at is None
    container.store.upsert(events)
    detail = container.trackers().conflict_detail("ukraine")
    assert detail.card.activity.last_7d == 1 and detail.card.fatalities_7d == 4
    outside = events[0].with_changes(id="outside", point=Point(0, 0), country_iso="UA")
    container.store.upsert([outside])
    assert container.trackers().conflict_detail("ukraine").card.activity.last_7d == 1
