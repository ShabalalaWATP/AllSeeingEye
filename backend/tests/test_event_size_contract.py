"""Exact byte-accounting contributions and eviction thresholds for public events."""

from datetime import timedelta
from types import MappingProxyType

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.adapters.store.sizing import estimate_bytes
from ase.application.feeds.budgets import RetentionBudget
from ase.domain.events import Category, Event, Reliability
from feeds_helpers import NOW
from test_live_snapshot_file import rich_event


def minimal_event() -> Event:
    return Event(
        id="e",
        source_id="s",
        category=Category.DISASTER,
        subtype="",
        title="",
        published_at=None,
        observed_at=NOW,
        reliability=Reliability.A,
        language="",
    )


def test_empty_optional_fields_keep_fixed_overhead_and_required_text_contribution() -> None:
    assert estimate_bytes(minimal_event()) == 1_032


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "source_id",
        "subtype",
        "title",
        "summary",
        "url",
        "language",
        "title_en",
        "country_iso",
        "grade_rationale",
        "story_id",
        "content_hash",
    ],
)
@pytest.mark.parametrize("text", ["", "longer text", "\u2603\U0001f9ea"])
def test_every_public_text_field_preserves_its_codepoint_based_contribution(
    field: str, text: str
) -> None:
    original = minimal_event()
    changed = original.with_changes(**{field: text})
    expected_delta = 4 * (len(text) - len(getattr(original, field) or ""))
    assert estimate_bytes(changed) - estimate_bytes(original) == expected_delta


def test_attribute_scalar_conversion_and_tag_overheads_remain_exact() -> None:
    event = minimal_event().with_changes(
        attributes=MappingProxyType(
            {"x": None, "count": 123, "flag": True, "ratio": 0.5, "note": "\u2603"}
        ),
        tags=frozenset({"a", "snow\u2603"}),
    )
    # Attributes contribute116+128+128+128+116; tags contribute68+84.
    assert estimate_bytes(event) == 1_800


def test_rich_evidence_keeps_the_frozen_accounting_total() -> None:
    # Captured from the unchanged 13e9525d accounting contract before this refactor.
    assert estimate_bytes(rich_event()) == 7_512


@pytest.mark.parametrize(
    ("field", "contribution"),
    [
        ("geometry", 391),
        ("observation", 283),
        ("project", 706),
        ("transformations", 1_852),
        ("source_dates", 1_712),
    ],
)
def test_each_complex_evidence_contribution_remains_in_the_estimate(
    field: str, contribution: int
) -> None:
    event = rich_event()
    empty = () if field in ("transformations", "source_dates") else None
    assert estimate_bytes(event.with_changes(**{field: empty})) == 7_512 - contribution


@pytest.mark.parametrize(
    ("offset", "expected_ids"), [(-1, ["b"]), (0, ["a", "b"]), (1, ["a", "b"])]
)
def test_restore_enforces_the_exact_memory_boundary_and_oldest_first_eviction(
    offset: int, expected_ids: list[str]
) -> None:
    earlier = minimal_event().with_changes(id="a", observed_at=NOW - timedelta(minutes=1))
    later = minimal_event().with_changes(id="b")
    budget = 2_064 + offset
    store = InMemoryEventStore(memory_budget_bytes=budget)
    assert store.restore([earlier, later], NOW) == len(expected_ids)
    assert [event.id for event in store.retained()] == expected_ids
    assert store.runtime_stats() == (len(expected_ids), 1_032 * len(expected_ids), budget)


def test_restore_keeps_retention_and_duplicate_rules_with_byte_accounting() -> None:
    store = InMemoryEventStore(
        budgets={Category.DISASTER: RetentionBudget(timedelta(hours=1), 1)},
        memory_budget_bytes=10_000,
    )
    expired = minimal_event().with_changes(id="a", observed_at=NOW - timedelta(hours=2))
    earlier = minimal_event().with_changes(id="b", observed_at=NOW - timedelta(minutes=1))
    latest = minimal_event().with_changes(id="c")
    duplicate = latest.with_changes(title="Must not replace first snapshot occurrence")
    assert store.restore([expired, earlier, latest, duplicate], NOW) == 1
    assert store.retained() == [latest]
    assert store.runtime_stats() == (1, 1_032, 10_000)
