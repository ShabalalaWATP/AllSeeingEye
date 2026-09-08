"""Public NOAA-20 CSV contract and collection bounds, with no external network."""

import csv
import io
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds import firms_public
from ase.adapters.feeds.firms_public import (
    PUBLIC_FIRMS,
    PUBLIC_URL,
    FirmsPublicConnector,
    parse_public_firms,
)
from ase.adapters.feeds.http import FeedFetchError
from feeds_helpers import FakeClock
from test_firms_feed import NOW, ROW


def payload(**changes):
    row = {key: value for key, value in ROW.items() if key != "instrument"}
    row["confidence"] = "nominal"
    row.update(changes)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    return output.getvalue().encode()


@pytest.mark.parametrize("confidence,code", [("low", "l"), ("nominal", "n"), ("high", "h")])
def test_normalises_documented_public_confidence_and_preserves_provenance(confidence, code):
    event = parse_public_firms(payload(confidence=confidence), NOW)[0]
    assert event.source_id == PUBLIC_FIRMS.id
    assert dict(event.attributes)["sensor_confidence"] == code
    assert dict(event.attributes)["instrument"] == "VIIRS"
    assert event.observation.acquired_at == event.published_at
    assert "does not establish" in event.summary
    assert not PUBLIC_FIRMS.requires_key
    assert parse_public_firms(payload(confidence=confidence), NOW)[0].id == event.id


@pytest.mark.parametrize(
    "changes",
    [
        {"confidence": "certain"},
        {"latitude": "91"},
        {"longitude": "nan"},
        {"satellite": "N21"},
        {"instrument": "MODIS"},
        {"acq_date": "2020-01-01"},
        {"frp": "inf"},
    ],
)
def test_rejects_invalid_or_stale_observations(changes):
    with pytest.raises(FeedFetchError, match="invalid observation"):
        parse_public_firms(payload(**changes), NOW)


def test_rejects_oversize_and_malformed_batches(monkeypatch):
    monkeypatch.setattr(firms_public, "MAX_PUBLIC_BYTES", 2)
    with pytest.raises(FeedFetchError, match="byte limit"):
        parse_public_firms(payload(), NOW)
    monkeypatch.setattr(firms_public, "MAX_PUBLIC_BYTES", 1024)
    monkeypatch.setattr(firms_public, "MAX_PUBLIC_ROWS", 0)
    with pytest.raises(FeedFetchError, match="row limit"):
        parse_public_firms(payload(), NOW)
    for value in (b"invalid", b"latitude,latitude\n1,1", b"\xff"):
        with pytest.raises(FeedFetchError, match="invalid observation"):
            parse_public_firms(value, NOW)


async def test_fetches_only_fixed_official_no_key_url_without_redirects():
    http = AsyncMock()
    http.get_bytes.return_value = payload()
    assert len(await FirmsPublicConnector(http, FakeClock(NOW)).fetch()) == 1
    http.get_bytes.assert_awaited_once_with(PUBLIC_URL, max_redirects=0)
