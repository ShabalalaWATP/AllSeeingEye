"""Explicit numeric offsets written with a colon are declared values, not guesses."""

from datetime import UTC, datetime

import pytest

from ase.domain.source_dates import resolve_source_date


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Tue, 01 Sep 2026 10:00:00 -04:00", datetime(2026, 9, 1, 14, tzinfo=UTC)),
        ("Tue, 01 Sep 2026 10:00:00 +05:30", datetime(2026, 9, 1, 4, 30, tzinfo=UTC)),
        ("Fri, 11 Sep 26 12:00:00 +0000", datetime(2026, 9, 11, 12, tzinfo=UTC)),
    ],
)
def test_rfc_822_offsets_with_colons_resolve_without_changing_the_declared_zone(raw, expected):
    resolved = resolve_source_date(raw, "pubDate", "gregorian", basis="source_spec")
    assert resolved.status == "resolved" and resolved.value == expected


@pytest.mark.parametrize(
    ("raw", "status"),
    [
        ("Tue, 01 Sep 2026 10:00:00", "ambiguous"),
        ("Tue, 01 Sep 2026 10:00:00 -04:0", "ambiguous"),
        ("yesterday -04:00", "invalid"),
    ],
)
def test_missing_or_malformed_offsets_are_not_completed(raw, status):
    resolved = resolve_source_date(raw, "pubDate", "gregorian", basis="source_spec")
    assert resolved.status == status and resolved.value is None
