"""Separate NOAA-20/21 observations with fixed product URLs and shared credential rules."""

from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.firms import FirmsConnector, parse_firms
from ase.adapters.feeds.firms_public import FirmsPublicConnector, parse_public_firms
from ase.adapters.feeds.firms_sensors import NOAA20, NOAA21
from ase.adapters.feeds.http import FeedFetchError
from feeds_helpers import FakeClock
from test_firms_feed import NOW, ROW, payload
from test_firms_public import payload as public_payload


@pytest.mark.parametrize("code", ["N21", "2"])
def test_noaa21_keeps_its_sensor_product_and_source_identity(code):
    event = parse_firms(payload({**ROW, "satellite": code}), NOW, NOAA21)[0]
    assert event.source_id == "firms_viirs_noaa21"
    assert event.title == "NOAA-21 VIIRS thermal detection"
    assert event.attributes["satellite"] == "NOAA-21"
    assert event.observation.collection_id == "VIIRS_NOAA21_NRT"
    noaa20 = parse_firms(payload(ROW), NOW, NOAA20)[0]
    assert noaa20.id != event.id


@pytest.mark.parametrize("sensor,code", [(NOAA20, "N21"), (NOAA21, "N20")])
def test_cross_sensor_rows_are_rejected(sensor, code):
    with pytest.raises(FeedFetchError):
        parse_firms(payload({**ROW, "satellite": code}), NOW, sensor)


def test_public_noaa21_normalises_confidence_without_losing_identity():
    event = parse_public_firms(public_payload(satellite="N21", confidence="high"), NOW, NOAA21)[0]
    assert event.source_id == "firms_public_noaa21"
    assert event.attributes["sensor_confidence"] == "h"
    assert event.observation.collection_id == "VIIRS_NOAA21_NRT"


def test_negative_provider_power_is_flagged_and_preserved_without_inventing_valid_power():
    event = parse_public_firms(public_payload(satellite="N21", frp="-0.53"), NOW, NOAA21)[0]
    assert event.attributes["fire_radiative_power_mw"] is None
    assert event.attributes["reported_fire_radiative_power_mw"] == -0.53
    assert "negative radiative power" in event.summary
    assert event.observation.limitations == event.summary


async def test_keyed_and_public_noaa21_use_only_fixed_official_products():
    http = AsyncMock()
    http.get_secret_bytes.return_value = payload({**ROW, "satellite": "N21"})
    http.get_bytes.return_value = public_payload(satellite="N21")
    keyed = FirmsConnector(http, FakeClock(NOW), "synthetic_key_123456789", sensor=NOAA21)
    assert len(await keyed.fetch()) == 1
    assert "VIIRS_NOAA21_NRT/world/2" in http.get_secret_bytes.call_args.args[0].url
    public = FirmsPublicConnector(http, FakeClock(NOW), sensor=NOAA21)
    assert len(await public.fetch()) == 1
    http.get_bytes.assert_awaited_once_with(
        "https://firms.modaps.eosdis.nasa.gov" + NOAA21.public_path, max_redirects=0
    )


def test_unlisted_products_cannot_construct_upstream_urls():
    sensor = replace(NOAA21, product="../../other", public_path="https://other.example")
    for constructor in (
        lambda: FirmsConnector(
            AsyncMock(), FakeClock(NOW), "synthetic_key_123456789", sensor=sensor
        ),
        lambda: FirmsPublicConnector(AsyncMock(), FakeClock(NOW), sensor=sensor),
    ):
        with pytest.raises(ValueError, match="Unsupported FIRMS sensor"):
            constructor()


@pytest.mark.parametrize("sensor,code", [(NOAA20, "N20"), (NOAA21, "N21")])
async def test_midnight_restart_collects_previous_calendar_day(sensor, code):
    midnight = datetime(2026, 9, 8, 0, 30, tzinfo=UTC)

    class Http:
        async def get_secret_bytes(self, target):
            # NASA returns only today's rows for /1. The previous day's delivery
            # remains available through /2 when today's file is still empty.
            if target.url.endswith("/world/2"):
                return payload({**ROW, "satellite": code, "acq_time": "2315"})
            return payload()

    connector = FirmsConnector(
        Http(), FakeClock(midnight), "synthetic_key_123456789", sensor=sensor
    )
    events = await connector.fetch()
    assert len(events) == 1
    assert events[0].published_at == datetime(2026, 9, 7, 23, 15, tzinfo=UTC)
    assert events[0].observed_at == midnight
