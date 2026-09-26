"""Strict decoding of live-store snapshot records: unknown or invalid values never load."""

from __future__ import annotations

from typing import Any

import pytest

from ase.adapters.store.snapshot_codec import REQUIRED_FIELDS, event_from_record, event_to_record
from ase.domain.events import Credibility, GeoConfidence
from feeds_helpers import make_event

RECORD = event_to_record(make_event("a"))
INVALID: list[dict[str, Any]] = [
    {"id": ""},
    {"id": 7},
    {"title": 5},
    {"title": "x" * 20_001},
    {"category": "unknown"},
    {"category": ["news"]},
    {"reliability": "Z"},
    {"geo_confidence": "street"},
    {"credibility": True},
    {"credibility": 9},
    {"observed_at": "2026-09-05T00:00:00"},
    {"observed_at": "yesterday"},
    {"published_at": 7},
    {"point": [200.0, 0.0]},
    {"point": [1.0]},
    {"point": [True, 0.0]},
    {"point": [None, 0.0]},
    {"point": "0,0"},
    {"severity": "high"},
    {"severity": float("inf")},
    {"tags": "abc"},
    {"tags": [1]},
    {"tags": ["t"] * 201},
    {"attributes": []},
    {"attributes": {"a": [1]}},
    {"attributes": {"a": {"nested": 1}}},
    {"attributes": {"a": float("nan")}},
    {"attributes": {"a": "x" * 20_001}},
    {"attributes": {str(key): key for key in range(101)}},
    {"summary": 3},
    {"country_iso": ["GB"]},
    {"content_hash": None},
    {"transformations": [{"bogus": 1}]},
    {"transformations": "x"},
    {"source_dates": [{}]},
    {"source_dates": [1]},
    {"geometry": {"x": 1}},
    {"observation": {"acquired_at": "now"}},
    {"project": {"dataset_id": "x"}},
]


@pytest.mark.parametrize("changes", INVALID, ids=[str(i) for i in range(len(INVALID))])
def test_invalid_values_are_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        event_from_record(RECORD | changes)


@pytest.mark.parametrize("record", ["text", ["list"], None, RECORD | {"unknown": 1}])
def test_non_records_and_unknown_fields_are_rejected(record: object) -> None:
    with pytest.raises(ValueError):
        event_from_record(record)


def test_missing_required_fields_are_rejected() -> None:
    for name in REQUIRED_FIELDS:
        with pytest.raises(ValueError):
            event_from_record({key: value for key, value in RECORD.items() if key != name})


def test_absent_optional_fields_take_event_defaults() -> None:
    event = event_from_record({key: RECORD[key] for key in REQUIRED_FIELDS})
    assert event.language == "en"
    assert event.tags == frozenset()
    assert event.geo_confidence is GeoConfidence.NONE
    assert event.credibility is Credibility.CANNOT_BE_JUDGED
    assert dict(event.attributes) == {}
    assert (event.point, event.geometry, event.transformations) == (None, None, ())
