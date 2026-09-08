"""Disk bounds, corrupt-input handling and atomic orbital-cache replacement."""

import json
from datetime import timedelta
from pathlib import Path

import pytest

from ase.adapters.feeds.satellite_cache import (
    MAX_CACHE_BYTES,
    ElementState,
    SatelliteCache,
    bounded_rows,
)
from ase.adapters.feeds.satellites import ACTIVE_SATELLITES
from feeds_helpers import NOW
from test_satellite_catalogues import elements


def cache_at(directory: Path) -> SatelliteCache:
    return SatelliteCache(directory, ACTIVE_SATELLITES.id, ACTIVE_SATELLITES.url)


def cached_state() -> ElementState:
    return ElementState(bounded_rows([elements()]), NOW, NOW + timedelta(hours=2))


def test_round_trip_and_fixed_paths(tmp_path: Path) -> None:
    cache = cache_at(tmp_path)
    assert not cache.load(NOW).rows
    state = cached_state()
    cache.save(state)
    assert cache.load(NOW) == state
    assert [p.suffix for p in tmp_path.iterdir()] == [".json"]
    with pytest.raises(ValueError, match="Unsupported"):
        SatelliteCache(tmp_path, "../../escape", "https://example.com")


@pytest.mark.parametrize(
    "change",
    [
        {"version": 99},
        {"source_id": "other"},
        {"url": "https://other.test"},
        {"fetched_at": (NOW + timedelta(days=1)).isoformat()},
        {"retry_at": (NOW + timedelta(days=1)).isoformat()},
        {"fetched_at": NOW.replace(tzinfo=None).isoformat()},
        {"fetched_at": None},
        {"rows": [{"not": "orbital elements"}]},
    ],
)
def test_invalid_cache_does_not_reset_request_budget(tmp_path: Path, change: dict) -> None:
    cache = cache_at(tmp_path)
    cache.save(cached_state())
    data = json.loads(cache.path.read_bytes())
    cache.path.write_bytes(json.dumps({**data, **change}).encode())
    recovered = cache.load(NOW)
    assert not recovered.rows
    assert recovered.retry_at == NOW + timedelta(hours=2)
    assert "unreadable" in recovered.error


@pytest.mark.parametrize(
    "data",
    [b"not JSON", b"[]", b"x" * (MAX_CACHE_BYTES + 1)],
    ids=["invalid-json", "wrong-shape", "over-byte-limit"],
)
def test_corrupt_or_oversize_cache_is_bounded(tmp_path: Path, data: bytes) -> None:
    cache = cache_at(tmp_path)
    cache.path.write_bytes(data)
    assert cache.load(NOW).error


def test_failed_replace_keeps_previous_cache(tmp_path: Path, monkeypatch) -> None:
    cache = cache_at(tmp_path)
    cache.save(cached_state())
    original = cache.path.read_bytes()

    def failed(*args):
        raise OSError("Read-only filesystem")

    monkeypatch.setattr("ase.adapters.feeds.satellite_cache.os.replace", failed)
    with pytest.raises(OSError):
        cache.save(ElementState(error="new failure", retry_at=NOW))
    assert cache.path.read_bytes() == original
    assert len(list(tmp_path.iterdir())) == 1


def test_byte_limit_rejects_replacement(tmp_path: Path, monkeypatch) -> None:
    cache = cache_at(tmp_path)
    cache.save(cached_state())
    original = cache.path.read_bytes()
    monkeypatch.setattr("ase.adapters.feeds.satellite_cache.MAX_CACHE_BYTES", 10)
    with pytest.raises(OSError, match="byte limit"):
        cache.save(cached_state())
    assert cache.path.read_bytes() == original


def test_omm_optional_designator_and_scalar_allowlist() -> None:
    row = elements()
    del row["OBJECT_ID"]
    clean = bounded_rows([None, {**row, "extra": {"large": "object"}}])[0]
    assert clean["OBJECT_ID"] == ""
    assert "extra" not in clean
    with pytest.raises(ValueError):
        bounded_rows([])
