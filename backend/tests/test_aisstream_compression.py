"""Subscription compression diagnostics preserve valid AIS positions and safe warnings."""

import pytest

from ase.adapters.feeds import aisstream
from feeds_helpers import NOW, FakeClock
from test_aisstream import message, setup


def confirmation(value):
    return {"MessageType": "SubscriptionConfirmation", "Message": value}


@pytest.mark.parametrize(
    "payload,degraded",
    [
        ({"CompressionEnabled": False}, True),
        ({"CompressionEnabled": True}, False),
        ({"CompressionEnabled": "false"}, False),
        ({"CompressionEnabled": 0}, False),
        ({"CompressionEnabled": None}, False),
        ({}, False),
        (None, False),
        ([], False),
    ],
)
async def test_binary_confirmation_only_explicit_false_warns(monkeypatch, payload, degraded):
    socket, options = setup(monkeypatch, [confirmation(payload), message()])
    connector = aisstream.AisStreamConnector("test-key", FakeClock(NOW))

    events = await connector.fetch()

    assert len(events) == 1 and events[0].published_at == NOW
    assert socket.closed and options["compression"] == "deflate"
    if degraded:
        assert "compression" in connector.warning.lower()
        assert "bandwidth" in connector.warning.lower()
        assert "test-key" not in connector.warning
    else:
        assert connector.warning is None


async def test_legacy_positions_without_confirmation_remain_usable(monkeypatch):
    setup(monkeypatch, [message()])
    connector = aisstream.AisStreamConnector("test-key", FakeClock(NOW))
    assert len(await connector.fetch()) == 1
    assert connector.warning is None


@pytest.mark.parametrize("limit", ["MAX_MESSAGES", "MAX_VESSELS"])
async def test_compression_warning_survives_collection_limits(monkeypatch, limit):
    setup(monkeypatch, [confirmation({"CompressionEnabled": False}), message()])
    monkeypatch.setattr(aisstream, limit, 2 if limit == "MAX_MESSAGES" else 1)
    connector = aisstream.AisStreamConnector("test-key", FakeClock(NOW))

    assert len(await connector.fetch()) == 1
    assert "compression" in connector.warning.lower()
    assert "collection limit reached" in connector.warning.lower()


async def test_compression_warning_survives_interruption_without_provider_text(monkeypatch):
    setup(
        monkeypatch,
        [confirmation({"CompressionEnabled": False}), message(), {"error": "test-key"}],
    )
    connector = aisstream.AisStreamConnector("test-key", FakeClock(NOW))

    assert len(await connector.fetch()) == 1
    assert "compression" in connector.warning.lower()
    assert "interrupted" in connector.warning.lower()
    assert "test-key" not in connector.warning


async def test_compression_warning_is_bounded_and_reset_for_next_connection(monkeypatch):
    setup(
        monkeypatch,
        [confirmation({"CompressionEnabled": False}) for _ in range(3)] + [message()],
    )
    connector = aisstream.AisStreamConnector("test-key", FakeClock(NOW))

    assert len(await connector.fetch()) == 1
    assert connector.warning.lower().count("compression") == 1

    setup(monkeypatch, [confirmation({"CompressionEnabled": True}), message()])
    assert len(await connector.fetch()) == 1
    assert connector.warning is None
