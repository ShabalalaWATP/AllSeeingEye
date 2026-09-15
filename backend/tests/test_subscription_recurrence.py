"""Calendar previews and immutable subscription request windows across DST."""

from datetime import UTC, datetime, timedelta

import pytest

from ase.domain.subscription_recurrence import (
    LocalRecurrence,
    WindowPolicy,
    requested_window,
)


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def test_spring_gap_uses_first_valid_local_minute() -> None:
    recurrence = LocalRecurrence("Europe/London", 1, 30, "daily")
    slots = recurrence.next_three(_utc(2026, 3, 28, 1, 30))
    assert [slot.utc for slot in slots] == [
        _utc(2026, 3, 29, 1),
        _utc(2026, 3, 30, 0, 30),
        _utc(2026, 3, 31, 0, 30),
    ]
    assert (slots[0].local.hour, slots[0].local.minute) == (2, 0)
    assert slots[0].dst_resolution == "gap"
    assert slots[0].scheduled_date.isoformat() == "2026-03-29"


def test_autumn_fold_uses_earlier_occurrence_once() -> None:
    recurrence = LocalRecurrence("Europe/London", 1, 30, "daily")
    slots = recurrence.preview(_utc(2026, 10, 24, 0, 30), 2)
    assert slots[0].utc == _utc(2026, 10, 25, 0, 30)
    assert slots[0].local.fold == 0
    assert slots[0].dst_resolution == "fold"
    assert slots[1].utc == _utc(2026, 10, 26, 1, 30)
    assert recurrence.preview(_utc(2026, 10, 25, 0, 45), 1)[0].utc == _utc(2026, 10, 26, 1, 30)


def test_month_end_anchor_survives_short_months_and_leap_years() -> None:
    monthly = LocalRecurrence("UTC", 9, 15, "monthly", monthday=31)
    assert [slot.utc for slot in monthly.next_three(_utc(2026, 1, 31, 9, 15))] == [
        _utc(2026, 2, 28, 9, 15),
        _utc(2026, 3, 31, 9, 15),
        _utc(2026, 4, 30, 9, 15),
    ]
    annual = LocalRecurrence("UTC", 9, 0, "annual", monthday=29, anchor_month=2)
    assert [slot.utc for slot in annual.next_three(_utc(2031, 2, 27))] == [
        _utc(2031, 2, 28, 9),
        _utc(2032, 2, 29, 9),
        _utc(2033, 2, 28, 9),
    ]
    quarterly = LocalRecurrence("UTC", 9, 0, "quarterly", monthday=31, anchor_month=2)
    assert [slot.utc for slot in quarterly.next_three(_utc(2026, 1, 1))] == [
        _utc(2026, 2, 28, 9),
        _utc(2026, 5, 31, 9),
        _utc(2026, 8, 31, 9),
    ]


def test_weekday_and_weekly_previews_keep_local_calendar_date() -> None:
    weekdays = LocalRecurrence("Europe/London", 8, 5, "weekdays")
    assert [
        slot.scheduled_date.isoformat() for slot in weekdays.next_three(_utc(2026, 9, 4, 8))
    ] == [
        "2026-09-07",
        "2026-09-08",
        "2026-09-09",
    ]
    weekly = LocalRecurrence("UTC", 12, 0, "weekly", weekday=4)
    assert weekly.preview(_utc(2026, 9, 4, 12), 1)[0].utc == _utc(2026, 9, 11, 12)


@pytest.mark.parametrize(
    "values",
    [
        {"timezone": "No/Such_Zone"},
        {"hour": 24},
        {"minute": 60},
        {"cadence": "hourly"},
        {"monthday": 0},
        {"anchor_month": 13},
    ],
)
def test_invalid_recurrence_is_rejected(values: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        LocalRecurrence(**{"timezone": "UTC", "hour": 9, "minute": 0, "cadence": "daily", **values})


def test_preview_rejects_naive_reference_and_unbounded_count() -> None:
    recurrence = LocalRecurrence("UTC", 9, 0, "daily")
    with pytest.raises(ValueError):
        recurrence.next_three(datetime(2026, 9, 1))
    with pytest.raises(ValueError):
        recurrence.preview(_utc(2026, 9, 1), 13)


def test_rolling_snapshot_remains_anchored_to_due_slot_when_late() -> None:
    due = _utc(2026, 9, 1, 12)
    window = requested_window(WindowPolicy.ROLLING_SNAPSHOT, due, timedelta(days=30))
    assert window.interval is not None
    assert window.interval.start == due - timedelta(days=30)
    assert window.interval.end == due
    assert window.overlap == timedelta(hours=6)


def test_since_success_uses_complete_cutoff_and_quarter_span_overlap() -> None:
    due = _utc(2026, 9, 1, 12)
    cutoff = due - timedelta(hours=4)
    window = requested_window(
        WindowPolicy.SINCE_LAST_SUCCESS,
        due,
        timedelta(days=30),
        compatible_complete_cutoff=cutoff,
    )
    assert window.interval is not None
    assert window.overlap == timedelta(hours=1)
    assert window.interval.start == cutoff - timedelta(hours=1)
    assert window.interval.end == due
    # A later accepted analytical partial baseline is deliberately not a coverage cutoff.
    older_complete = due - timedelta(days=5)
    unresolved = requested_window(
        WindowPolicy.SINCE_LAST_SUCCESS,
        due,
        timedelta(days=30),
        compatible_complete_cutoff=older_complete,
    )
    assert unresolved.interval is not None
    assert unresolved.interval.start == older_complete - timedelta(hours=6)


def test_first_since_success_uses_initial_lookback_and_newer_cutoff_skips() -> None:
    due = _utc(2026, 9, 1, 12)
    first = requested_window(WindowPolicy.SINCE_LAST_SUCCESS, due, timedelta(hours=8))
    assert first.interval is not None
    assert first.interval.start == due - timedelta(hours=8)
    assert first.overlap == timedelta(hours=2)
    for cutoff in (due, due + timedelta(hours=1)):
        skipped = requested_window(
            WindowPolicy.SINCE_LAST_SUCCESS,
            due,
            timedelta(hours=8),
            compatible_complete_cutoff=cutoff,
        )
        assert skipped.interval is None and skipped.covered_by_newer


def test_invalid_window_inputs_are_rejected() -> None:
    due = _utc(2026, 9, 1, 12)
    for lookback in (timedelta(), timedelta(days=731)):
        with pytest.raises(ValueError):
            requested_window(WindowPolicy.ROLLING_SNAPSHOT, due, lookback)
    with pytest.raises(ValueError):
        requested_window(WindowPolicy.ROLLING_SNAPSHOT, datetime(2026, 9, 1), timedelta(days=1))
    with pytest.raises(ValueError):
        requested_window("unbounded", due, timedelta(days=1))  # type: ignore[arg-type]
