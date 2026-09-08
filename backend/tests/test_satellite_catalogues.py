"""Public satellite catalogue bounds, source labels and propagation freshness."""

import csv
import io
from datetime import timedelta
from typing import Any

import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.satellites import (
    ACTIVE_SATELLITES,
    MAX_OBJECTS,
    MILITARY_SATELLITES,
    SATELLITE_SPECS,
    SKYNET_SATELLITES,
    SatelliteConnector,
    orbital_epoch,
)
from feeds_helpers import NOW, FakeHttp, load_fixture
from helpers import FakeClock


def elements(**changes: Any) -> dict[str, Any]:
    return {**load_fixture("celestrak_stations.json")[0], **changes}


def csv_catalogue(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


async def test_active_csv_loads_more_than_old_500_limit_and_deduplicates() -> None:
    rows = [elements(NORAD_CAT_ID=100_000 + index) for index in range(650)]
    rows.append(rows[0])
    http = FakeHttp({"gp.php": csv_catalogue(rows)})
    events = await SatelliteConnector(http, FakeClock(NOW), ACTIVE_SATELLITES).fetch()
    assert len(events) == 650
    assert len({event.id for event in events}) == 650
    assert events[0].attributes["norad_id"] == "100000"
    assert events[0].attributes["position_kind"] == "propagated"
    assert events[0].attributes["catalogue_group"] == "active"
    assert events[0].attributes["military_public_catalogue"] is False
    assert "stations" not in events[0].tags


async def test_csv_is_bounded_before_propagation(monkeypatch: pytest.MonkeyPatch) -> None:
    connector = SatelliteConnector(
        FakeHttp({"gp.php": csv_catalogue([elements()] * (MAX_OBJECTS + 2))}),
        FakeClock(NOW),
        ACTIVE_SATELLITES,
    )
    calls = []
    monkeypatch.setattr(connector, "_to_event", lambda fields, now: calls.append(fields))
    assert await connector.fetch() == []
    assert len(calls) == MAX_OBJECTS


async def test_invalid_csv_is_a_fetch_error_not_empty_success() -> None:
    with pytest.raises(ValueError, match="missing orbital fields"):
        await SatelliteConnector(
            FakeHttp({"gp.php": "<html>Unavailable</html>"}),
            FakeClock(NOW),
            ACTIVE_SATELLITES,
        ).fetch()


@pytest.mark.parametrize("name", ["SKYNET 5A", "SKYNET 4F"])
async def test_skynet_is_publicly_labelled_without_claiming_live_observation(name: str) -> None:
    events = await SatelliteConnector(
        FakeHttp({"gp.php": [elements(OBJECT_NAME=name)]}),
        FakeClock(NOW),
        SKYNET_SATELLITES,
    ).fetch()
    assert len(events) == 1
    assert {"skynet", "military-public", "propagated"} <= events[0].tags
    assert events[0].attributes["military_public_catalogue"] is True
    assert events[0].attributes["affiliation_basis"] == "Public Skynet satellite name"
    assert "not a live observation" in events[0].grade_rationale


@pytest.mark.parametrize("name", ["SKYNET 4A R/B [PAM-D2]", "SKYNET 5A DEB", "OTHER"])
async def test_skynet_search_does_not_invent_payloads(name: str) -> None:
    assert (
        await SatelliteConnector(
            FakeHttp({"gp.php": [elements(OBJECT_NAME=name)]}),
            FakeClock(NOW),
            SKYNET_SATELLITES,
        ).fetch()
        == []
    )


async def test_military_group_affiliation_has_explicit_basis() -> None:
    events = await SatelliteConnector(
        FakeHttp({"gp.php": [elements(OBJECT_NAME="SAR-LUPE 2")]}),
        FakeClock(NOW),
        MILITARY_SATELLITES,
    ).fetch()
    assert events[0].attributes["affiliation_basis"] == "CelesTrak military group"
    assert "skynet" not in events[0].tags


@pytest.mark.parametrize(
    "changes",
    [
        {"NORAD_CAT_ID": "bad"},
        {"NORAD_CAT_ID": "Â²"},
        {"NORAD_CAT_ID": "9" * 5000},
        {"NORAD_CAT_ID": 0},
        {"NORAD_CAT_ID": 1_000_000_000},
        {"EPOCH": "bad"},
        {"EPOCH": (NOW - timedelta(days=15)).isoformat()},
        {"EPOCH": (NOW + timedelta(days=2)).isoformat()},
        {"MEAN_MOTION": "bad"},
        {"ECCENTRICITY": 2},
        {"INCLINATION": "nan"},
    ],
)
async def test_invalid_or_expired_elements_are_not_positions(changes: dict[str, Any]) -> None:
    assert (
        await SatelliteConnector(
            FakeHttp({"gp.php": [elements(**changes)]}),
            FakeClock(NOW),
        ).fetch()
        == []
    )


async def test_stale_epoch_is_labelled_and_cache_refreshes_after_two_hours() -> None:
    http = FakeHttp({"gp.php": [elements(EPOCH=(NOW - timedelta(days=4)).isoformat())]})
    clock = FakeClock(NOW)
    connector = SatelliteConnector(http, clock)
    event = (await connector.fetch())[0]
    assert event.attributes["is_stale"] is True
    assert event.attributes["epoch_age_hours"] == 96
    assert "over three days old" in event.grade_rationale
    clock.advance(timedelta(hours=2))
    await connector.fetch()
    assert len(http.requests) == 2


async def test_not_modified_retains_elements() -> None:
    http = FakeHttp({"gp.php": [elements()]})
    clock = FakeClock(NOW)
    connector = SatelliteConnector(http, clock)
    assert len(await connector.fetch()) == 1
    clock.advance(timedelta(hours=2))
    http.not_modified = True
    assert len(await connector.fetch()) == 1


def test_specs_and_epoch_contract() -> None:
    assert len({spec.id for spec in SATELLITE_SPECS}) == 4
    assert all(spec.url.startswith("https://celestrak.org/") for spec in SATELLITE_SPECS)
    assert orbital_epoch(None) is None
    assert orbital_epoch("2026-09-05T00:00:00") == NOW
    assert orbital_epoch("2026-09-05T01:00:00+01:00") == NOW


async def test_failed_retrieval_obeys_two_hour_network_backoff() -> None:

    class FailingHttp(FakeHttp):
        async def get_json(self, url: str, *, conditional: bool = True) -> Any:
            self.requests.append(url)
            raise FeedFetchError("HTTP 403 from public catalogue")

    http = FailingHttp()
    clock = FakeClock(NOW)
    connector = SatelliteConnector(http, clock)
    with pytest.raises(FeedFetchError, match="403"):
        await connector.fetch()
    clock.advance(timedelta(minutes=2))
    with pytest.raises(FeedFetchError, match="waiting two hours"):
        await connector.fetch()
    assert len(http.requests) == 1
    clock.advance(timedelta(hours=2))
    with pytest.raises(FeedFetchError, match="403"):
        await connector.fetch()
    assert len(http.requests) == 2
