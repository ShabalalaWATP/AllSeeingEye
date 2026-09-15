"""Synthetic NASA Area API contract, limits and key-free observation metadata."""

import csv
import io
from datetime import UTC, datetime

import pytest

from ase.adapters.feeds import firms
from ase.adapters.feeds.firms import FirmsConnector, parse_firms, validate_area
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.registry import build_connectors
from ase.domain.events import Credibility, Reliability
from feeds_helpers import FakeClock, FakeHttp

NOW = datetime(2026, 9, 7, 12, tzinfo=UTC)
KEY = "synthetic_firms_key_12345"
ROW = dict(
    zip(
        [
            "latitude",
            "longitude",
            "bright_ti4",
            "scan",
            "track",
            "acq_date",
            "acq_time",
            "satellite",
            "instrument",
            "confidence",
            "version",
            "bright_ti5",
            "frp",
            "daynight",
        ],
        [
            "0",
            "0",
            "330",
            "0.4",
            "0.5",
            "2026-09-07",
            "5",
            "N20",
            "VIIRS",
            "n",
            "2.0NRT",
            "290",
            "12",
            "D",
        ],
        strict=True,
    )
)


def payload(*rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(ROW))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def test_acquisition_precision_confidence_and_stable_id():
    first = parse_firms(payload(ROW, ROW), NOW)
    assert len(first) == 1
    event = first[0]
    assert event.point.lon == event.point.lat == 0
    assert event.observation.acquired_at == datetime(2026, 9, 7, 0, 5, tzinfo=UTC)
    assert event.observed_at == NOW
    assert event.attributes["sensor_confidence"] == "n"
    assert event.subtype == "thermal_detection"
    assert event.source_id == "firms_viirs_noaa20"
    assert event.attributes["fire_radiative_power_mw"] == 12
    assert event.attributes["scan_km"] == 0.4
    assert event.reliability is Reliability.F
    assert event.credibility is Credibility.CANNOT_BE_JUDGED
    changed = parse_firms(payload({**ROW, "confidence": "h", "frp": "15"}), NOW)[0]
    assert changed.id == event.id and changed.content_hash != event.content_hash
    assert parse_firms(payload(), NOW) == []


@pytest.mark.parametrize(
    "change",
    [
        {"latitude": "nan"},
        {"longitude": "181"},
        {"frp": "inf"},
        {"scan": "-1"},
        {"acq_time": "2400"},
        {"acq_time": "5.0"},
        {"acq_date": "2026-09-01"},
        {"acq_date": "2026-09-09"},
        {"confidence": "99"},
        {"satellite": "N21"},
        {"instrument": "MODIS"},
        {"version": "<script>"},
        {"daynight": "X"},
    ],
)
def test_invalid_rows_reject_entire_batch(change):
    with pytest.raises(FeedFetchError, match="invalid observation batch"):
        parse_firms(payload(ROW, {**ROW, **change}), NOW)


@pytest.mark.parametrize("data", [b"Invalid MAP_KEY", b"\xff", b"", b"latitude,latitude\n1,2"])
def test_invalid_response_is_safe(data):
    with pytest.raises(FeedFetchError):
        parse_firms(data, NOW)


def test_collection_bounds(monkeypatch):
    monkeypatch.setattr(firms, "MAX_ROWS", 1)
    with pytest.raises(FeedFetchError, match="row limit"):
        parse_firms(payload(ROW, ROW), NOW)
    monkeypatch.setattr(firms, "MAX_BYTES", 1)
    with pytest.raises(FeedFetchError, match="byte limit"):
        parse_firms(payload(ROW), NOW)


def test_row_bound_admits_a_full_byte_budget_of_short_rows():
    # A real NOAA-21 two-date world response held 150,980 rows and broke a 150,000 cap.
    assert firms.MAX_ROWS > 150_980
    # The shortest observed row was 73 bytes, so a full byte budget stays within the cap.
    assert firms.MIN_ROW_BYTES < 73
    assert firms.MAX_ROWS * firms.MIN_ROW_BYTES > firms.MAX_BYTES - firms.MIN_ROW_BYTES


@pytest.mark.parametrize("area", ["0,0,0,1", "170,-10,-170,10", "nan,0,1,1", "world/x", "0,0,1"])
def test_bad_area_rejected(area):
    with pytest.raises(ValueError):
        validate_area(area)


async def test_connector_uses_protected_request_and_public_metadata():
    class Http:
        async def get_secret_bytes(self, target):
            assert KEY not in repr(target)
            assert target.url.endswith(f"/{KEY}/VIIRS_NOAA20_NRT/0,0,10,10/2")
            return payload(ROW)

    connector = FirmsConnector(Http(), FakeClock(NOW), KEY, "0,0,10,10")
    assert KEY not in repr(connector.spec)
    assert KEY not in repr(await connector.fetch())


def test_registry_opt_in_and_disable():
    kwargs = {"http": FakeHttp(), "clock": FakeClock(NOW)}
    assert firms.SPEC.id not in {c.spec.id for c in build_connectors(**kwargs)}
    assert firms.SPEC.id in {c.spec.id for c in build_connectors(**kwargs, firms_key=KEY)}
    assert firms.SPEC.id not in {
        c.spec.id
        for c in build_connectors(
            **kwargs,
            firms_key=KEY,
            disabled=[firms.SPEC.id],
        )
    }


@pytest.mark.parametrize("key", ["short", "x" * 129, "x" * 20 + "/", "x" * 20 + "\n"])
def test_invalid_key_does_not_echo(key):
    with pytest.raises(ValueError) as error:
        FirmsConnector(FakeHttp(), FakeClock(NOW), key)
    assert key not in str(error.value)
