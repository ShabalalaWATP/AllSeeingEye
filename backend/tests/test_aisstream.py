"""Global AIS validation, safe transport and bounded collection."""

import asyncio
import copy
import json
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds import aisstream
from ase.adapters.feeds.aisstream_positions import parse_position
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.registry import build_connectors
from feeds_helpers import NOW, FakeClock, FakeHttp


def message(kind="PositionReport"):
    return {
        "MessageType": kind,
        "MetaData": {"MMSI": 235123456, "ShipName": "TEST SHIP", "time_utc": NOW.isoformat()},
        "Message": {
            kind: {
                "UserID": 235123456,
                "Valid": True,
                "Latitude": 51.1,
                "Longitude": 1.5,
                "Sog": 0,
                "Cog": 90,
                "TrueHeading": 511,
            }
        },
    }


@pytest.mark.parametrize(
    "kind", ["PositionReport", "StandardClassBPositionReport", "ExtendedClassBPositionReport"]
)
def test_position_classes_keep_stationary_ship_and_heading_sentinel(kind):
    event = parse_position(message(kind), NOW)
    assert event and event.title == "TEST SHIP"
    assert event.attributes["speed_over_ground_knots"] == 0
    assert event.attributes["heading_deg"] is None
    assert event.attributes["track_deg"] == 90
    assert event.published_at == NOW


@pytest.mark.parametrize(
    "field,value",
    [
        ("Latitude", 91),
        ("Longitude", 181),
        ("Latitude", float("nan")),
        ("Valid", False),
        ("UserID", 7),
        ("Latitude", True),
    ],
)
def test_invalid_report_rejected(field, value):
    data = message()
    data["Message"]["PositionReport"][field] = value
    assert parse_position(data, NOW) is None


@pytest.mark.parametrize(
    "value",
    [
        None,
        123,
        "bad",
        "2026-09-05T00:00:00",
        (NOW - timedelta(minutes=16)).isoformat(),
        (NOW + timedelta(minutes=1)).isoformat(),
    ],
)
def test_missing_stale_future_or_ambiguous_time_rejected(value):
    data = message()
    data["MetaData"]["time_utc"] = value
    assert parse_position(data, NOW) is None


def test_provider_go_timestamp_and_malformed_messages():
    data = message()
    data["MetaData"]["time_utc"] = "2026-09-05 00:00:00.123456789 +0000 UTC"
    assert parse_position(data, NOW) is not None
    for bad in [
        {},
        {"MessageType": "PositionReport"},
        {"MessageType": []},
        {"MessageType": "SubscriptionConfirmation"},
    ]:
        assert parse_position(bad, NOW) is None


class Socket:
    def __init__(self, messages):
        self.messages = iter(messages)
        self.sent = []
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        self.closed = True

    async def send(self, data):
        self.sent.append(json.loads(data))

    async def recv(self):
        try:
            return json.dumps(next(self.messages)).encode()
        except StopIteration:
            await asyncio.sleep(5)


def setup(monkeypatch, messages):
    socket = Socket(messages)
    options = {}

    def connect(url, **kwargs):
        options.update(kwargs)
        assert url == aisstream.URL
        return socket

    monkeypatch.setattr(aisstream, "_DirectConnection", connect)
    monkeypatch.setattr(aisstream, "assert_public_host", AsyncMock(return_value="1.1.1.1"))
    monkeypatch.setattr(aisstream, "COLLECTION_SECONDS", 0.01)
    return socket, options


@pytest.mark.asyncio
async def test_bounded_collection_latest_per_vessel_and_secret_transport(monkeypatch):
    older = copy.deepcopy(message())
    older["MetaData"]["time_utc"] = (NOW - timedelta(seconds=1)).isoformat()
    socket, options = setup(
        monkeypatch, [message(), older, {"MessageType": "SubscriptionConfirmation"}]
    )
    events = await aisstream.AisStreamConnector("test-key", FakeClock(NOW)).fetch()
    assert len(events) == 1 and events[0].published_at == NOW
    assert socket.closed and socket.sent[0]["APIKey"] == "test-key"
    assert options["host"] == "1.1.1.1" and options["server_hostname"] == "stream.aisstream.io"
    assert options["proxy"] is None and options["max_size"] == 65536
    assert options["compression"] == "deflate"
    assert options["logger"].isEnabledFor(50) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [{"error": "test-key"}, [], None])
async def test_provider_errors_never_disclose_key_and_close(monkeypatch, data):
    socket, _ = setup(monkeypatch, [data])
    with pytest.raises(FeedFetchError) as error:
        await aisstream.AisStreamConnector("test-key", FakeClock(NOW)).fetch()
    assert "test-key" not in str(error.value) and socket.closed


@pytest.mark.asyncio
async def test_empty_window_is_visible_failure(monkeypatch):
    setup(monkeypatch, [])
    with pytest.raises(FeedFetchError, match="no fresh"):
        await aisstream.AisStreamConnector("key", FakeClock(NOW)).fetch()


@pytest.mark.asyncio
async def test_cancellation_closes_socket(monkeypatch):
    socket, _ = setup(monkeypatch, [])
    task = asyncio.create_task(aisstream.AisStreamConnector("key", FakeClock(NOW)).fetch())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert socket.closed


def test_registry_is_keyed_and_can_be_disabled():
    def ids(**kwargs):
        return {c.spec.id for c in build_connectors(FakeHttp(), FakeClock(NOW), **kwargs)}

    assert "aisstream" not in ids()
    assert "aisstream" in ids(aisstream_key="key")
    assert "aisstream" not in ids(aisstream_key="key", disabled=["aisstream"])


def test_redirect_refused():
    connection = aisstream._DirectConnection(aisstream.URL)
    assert isinstance(connection.process_redirect(ValueError("redirect")), FeedFetchError)
