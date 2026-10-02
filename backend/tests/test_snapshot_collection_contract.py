"""Small snapshot collections retain strict types, domain checks and error order."""

import math
from collections.abc import Iterator
from typing import Any

import pytest

from ase.adapters.store.snapshot_codec import event_from_record, event_to_record
from ase.domain.events import Point
from feeds_helpers import make_event
from test_live_snapshot_file import TRANSFORMATION


class FalseyList(list[Any]):
    def __bool__(self) -> bool:
        return False


class IteratedPoint(list[Any]):
    def __iter__(self) -> Iterator[Any]:
        return iter([10, 20])


def test_container_subclasses_keep_iteration_and_nonempty_validation() -> None:
    record = event_to_record(make_event("subclasses"))
    record["point"] = IteratedPoint([30, 40])
    assert event_from_record(record).point == Point(10, 20)
    record["tags"] = FalseyList(["retained"])
    assert event_from_record(record).tags == frozenset({"retained"})
    record["tags"] = FalseyList([None])
    with pytest.raises(ValueError, match="Invalid snapshot text"):
        event_from_record(record)
    record["tags"] = []
    record["transformations"] = FalseyList([dict(TRANSFORMATION)])
    assert len(event_from_record(record).transformations) == 1
    record["transformations"] = FalseyList([{**TRANSFORMATION, "method": ""}])
    with pytest.raises(ValueError):
        event_from_record(record)


@pytest.mark.parametrize("point", [[-180, -90], [180.0, 90.0], [-0.0, 0], [1, 2.5]])
def test_point_round_trip_preserves_number_types_and_signed_zero(point: list[Any]) -> None:
    record = event_to_record(make_event("point"))
    record["point"] = point
    restored = event_from_record(record)
    assert restored.point == Point(lon=point[0], lat=point[1])
    assert restored.point is not None
    assert type(restored.point.lon) is type(point[0])
    assert type(restored.point.lat) is type(point[1])
    assert math.copysign(1, restored.point.lon) == math.copysign(1, point[0])


@pytest.mark.parametrize(
    ("point", "message"),
    [
        ([], "Invalid snapshot point"),
        ((1, 2), "Invalid snapshot point"),
        ([1], "Invalid snapshot point"),
        ([1, 2, 3], "Invalid snapshot point"),
        ([True, 2], "Expected a finite number"),
        ([1, False], "Expected a finite number"),
        ([float("nan"), 0], "Expected a finite number"),
        ([0, float("inf")], "Expected a finite number"),
        ([None, 1], "Invalid snapshot point"),
        ([None, "bad"], "Expected a finite number"),
        ([181, "bad"], "Expected a finite number"),
        ([181, 0], "Coordinates out of range"),
        ([0, -91], "Coordinates out of range"),
    ],
)
def test_point_rejection_retains_numeric_then_domain_validation_order(
    point: Any, message: str
) -> None:
    record = event_to_record(make_event("point"))
    record["point"] = point
    with pytest.raises(ValueError, match=message):
        event_from_record(record)


@pytest.mark.parametrize("field", ["tags", "transformations"])
@pytest.mark.parametrize("value", [None, {}, "", 0, False])
def test_falsey_wrong_collection_types_remain_invalid(field: str, value: Any) -> None:
    record = event_to_record(make_event("wrong-type"))
    record[field] = value
    with pytest.raises(ValueError, match=r"Invalid snapshot tags|Invalid frozen transformations"):
        event_from_record(record)


def test_empty_collections_and_legacy_missing_fields_keep_public_defaults() -> None:
    event = make_event("empty").with_changes(tags=frozenset())
    record = event_to_record(event)
    assert event_from_record(record) == event
    record.pop("tags")
    record.pop("transformations")
    assert event_from_record(record) == event
    record["transformations"] = ()
    assert event_from_record(record) == event
    record["tags"] = ()
    with pytest.raises(ValueError, match="Invalid snapshot tags"):
        event_from_record(record)


def test_tags_retain_deduplication_limits_and_immutability() -> None:
    record = event_to_record(make_event("tags"))
    tags = ["雪", "alpha", "雪"]
    record["tags"] = tags
    restored = event_from_record(record)
    tags.append("later")
    assert restored.tags == frozenset({"雪", "alpha"})
    record["tags"] = ["x"] * 200
    assert event_from_record(record).tags == frozenset({"x"})
    record["tags"] = ["x"] * 201
    with pytest.raises(ValueError, match="Invalid snapshot tags"):
        event_from_record(record)
    for invalid in (["valid", 1], ["x" * 201]):
        record["tags"] = invalid
        with pytest.raises(ValueError, match="Invalid snapshot text"):
            event_from_record(record)


def test_nonempty_transformations_keep_domain_validation_and_cardinality() -> None:
    record = event_to_record(make_event("transformations"))
    record["transformations"] = [dict(TRANSFORMATION)] * 4
    restored = event_from_record(record)
    assert len(restored.transformations) == 4
    assert all(row.method == TRANSFORMATION["method"] for row in restored.transformations)
    record["transformations"] = [dict(TRANSFORMATION)] * 5
    with pytest.raises(ValueError, match="Invalid frozen transformations"):
        event_from_record(record)
    record["transformations"] = [dict(TRANSFORMATION), {**TRANSFORMATION, "method": ""}]
    with pytest.raises(ValueError):
        event_from_record(record)
