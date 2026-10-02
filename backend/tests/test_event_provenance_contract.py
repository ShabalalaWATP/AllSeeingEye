"""Public Event construction keeps immutable, bounded and typed provenance."""

from typing import Any

import pytest

from ase.adapters.store.snapshot_codec import event_from_record, event_to_record
from ase.domain.source_dates import resolve_source_date
from ase.domain.text_transformations import TextTransformation
from feeds_helpers import make_event

TRANSFORMATION = TextTransformation(
    field="title",
    original_text="Original title",
    transformed_text="Translated title",
    kind="translation",
    source_language="fr",
    target_language="en",
    origin="operator",
    method="Synthetic review",
)
SOURCE_DATE = resolve_source_date("2026-09-04", "publication", "gregorian")
ERROR = "Provenance requires at most four immutable transformations and dates"


@pytest.mark.parametrize("transformation_count", [0, 1, 4])
@pytest.mark.parametrize("date_count", [0, 1, 4])
def test_event_preserves_valid_provenance_and_snapshot_round_trip(
    transformation_count: int, date_count: int
) -> None:
    transformations = (TRANSFORMATION,) * transformation_count
    dates = (SOURCE_DATE,) * date_count
    event = make_event("provenance").with_changes(
        transformations=transformations, source_dates=dates
    )
    assert event.transformations is transformations
    assert event.source_dates is dates
    assert event_from_record(event_to_record(event)) == event


@pytest.mark.parametrize("field", ["transformations", "source_dates"])
@pytest.mark.parametrize("invalid", [None, [], {}, "", (None,), (object(),)])
def test_event_rejects_mutable_or_untyped_provenance(field: str, invalid: Any) -> None:
    with pytest.raises(ValueError, match=f"^{ERROR}$"):
        make_event("invalid").with_changes(**{field: invalid})


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("transformations", (TRANSFORMATION,) * 5),
        ("source_dates", (SOURCE_DATE,) * 5),
        ("transformations", (SOURCE_DATE,)),
        ("source_dates", (TRANSFORMATION,)),
        ("transformations", (TRANSFORMATION, object())),
        ("source_dates", (SOURCE_DATE, object())),
    ],
)
def test_event_rejects_overflow_wrong_kinds_and_invalid_later_members(
    field: str, invalid: tuple[object, ...]
) -> None:
    with pytest.raises(ValueError, match=f"^{ERROR}$"):
        make_event("invalid").with_changes(**{field: invalid})


@pytest.mark.parametrize("field", ["transformations", "source_dates"])
def test_snapshot_still_runs_nested_domain_validation(field: str) -> None:
    event = make_event("nested").with_changes(
        transformations=(TRANSFORMATION,), source_dates=(SOURCE_DATE,)
    )
    record = event_to_record(event)
    record[field][0]["method"] = ""
    with pytest.raises(ValueError):
        event_from_record(record)
