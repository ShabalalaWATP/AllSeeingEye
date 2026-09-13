"""Network outage feeds preserve provenance, country scope and credential boundaries."""

from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.network_outages import (
    CLOUDFLARE_RADAR,
    IODA_EVENTS,
    CloudflareRadarConnector,
    IodaEventsConnector,
)
from ase.adapters.feeds.registry import build_connectors
from ase.domain.events import GeoConfidence
from feeds_helpers import NOW, FakeHttp
from helpers import FakeClock


async def test_ioda_country_event_window_keeps_provider_scope_and_skips_old_or_asn_rows() -> None:
    start = int((NOW - timedelta(hours=2)).timestamp())
    payload = {
        "data": [
            {
                "location": "country/GB",
                "location_name": "United Kingdom",
                "start": start,
                "duration": 1800,
                "datasource": "bgp",
                "method": "median",
                "status": 0,
            },
            {"location": "asn/123", "start": start, "duration": 1800},
            {"location": "country/US", "start": start - 10 * 86400, "duration": 60},
            {"location": "country/FR", "start": start, "duration": float("nan")},
        ]
    }
    http = FakeHttp({"outages/events": payload})
    events = await IodaEventsConnector(http, FakeClock(NOW)).fetch()
    assert {event.country_iso for event in events} == {"GB", "FR"}
    gb = next(event for event in events if event.country_iso == "GB")
    assert "United Kingdom" in gb.title
    assert gb.geo_confidence is GeoConfidence.COUNTRY and gb.point is None
    assert gb.attributes["end"] is not None
    assert "not evidence of a cyberattack" in gb.attributes["attribution_status"]
    query = parse_qs(urlsplit(http.requests[0]).query)
    assert query["entityType"] == ["country"]
    assert query["limit"] == ["200"]
    assert IODA_EVENTS.independence_key == "Georgia Tech Internet Intelligence Lab (IODA)"


class CredentialHttp:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.url = ""
        self.credential = None

    async def get_json(self, url: str, *, credential, conditional: bool) -> object:
        self.url = url
        self.credential = credential
        return self.payload


async def test_cloudflare_annotations_map_only_reported_countries_and_keep_token_off_url() -> None:
    payload = {
        "success": True,
        "result": {
            "annotations": [
                {
                    "startDate": (NOW - timedelta(hours=2)).isoformat(),
                    "endDate": None,
                    "eventType": "OUTAGE",
                    "scope": "Multiple regions/cities",
                    "locations": ["UA", "GB", "UA", "XX/../../", 4],
                    "locationsDetails": [
                        {"code": "UA", "name": "Ukraine"},
                        {"code": "GB", "name": "United Kingdom"},
                    ],
                    "outage": {"outageType": "REGIONAL", "outageCause": "POWER_OUTAGE"},
                },
                {
                    "startDate": (NOW - timedelta(hours=1)).isoformat(),
                    "locations": [],
                    "asns": [64500],
                    "eventType": "OUTAGE",
                },
            ]
        },
    }
    http = CredentialHttp(payload)
    token = "test-token-only"
    events = await CloudflareRadarConnector(http, FakeClock(NOW), token).fetch()  # type: ignore[arg-type]
    assert {event.country_iso for event in events} == {"UA", "GB", None}
    assert all(
        event.geo_confidence is GeoConfidence.COUNTRY and event.point is None
        for event in events
        if event.country_iso
    )
    assert all(event.url == CLOUDFLARE_RADAR.homepage for event in events)
    assert any("Ukraine (regional)" in event.title for event in events)
    assert all(event.attributes["end"] is None for event in events)
    unlocated = next(event for event in events if event.country_iso is None)
    assert unlocated.geo_confidence is GeoConfidence.NONE and unlocated.point is None
    assert unlocated.attributes["entity_code"] == "64500"
    assert token not in http.url
    assert http.credential.authorization == f"Bearer {token}"
    assert http.credential.origin == "https://api.cloudflare.com"


@pytest.mark.parametrize("payload", [{"success": False}, {"success": True, "result": {}}])
async def test_cloudflare_schema_failures_are_reported_not_silent(payload: object) -> None:
    with pytest.raises(FeedFetchError):
        await CloudflareRadarConnector(
            CredentialHttp(payload),
            FakeClock(NOW),
            "test-token",  # type: ignore[arg-type]
        ).fetch()


def test_radar_requires_token_and_can_be_disabled_without_disabling_ioda() -> None:
    http = FakeHttp()
    without = {connector.spec.id for connector in build_connectors(http, FakeClock(NOW))}
    assert IODA_EVENTS.id in without and CLOUDFLARE_RADAR.id not in without
    with_token = {
        connector.spec.id
        for connector in build_connectors(http, FakeClock(NOW), cloudflare_radar_token="test-token")
    }
    assert CLOUDFLARE_RADAR.id in with_token
    disabled = {
        connector.spec.id
        for connector in build_connectors(
            http,
            FakeClock(NOW),
            disabled=[CLOUDFLARE_RADAR.id],
            cloudflare_radar_token="test-token",
        )
    }
    assert CLOUDFLARE_RADAR.id not in disabled and IODA_EVENTS.id in disabled
