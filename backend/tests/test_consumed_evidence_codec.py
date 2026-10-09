"""Fixed-size identity records fail closed and retain inclusive window boundaries."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.domain import consumed_evidence, warning
from ase.domain.consumed_evidence import (
    CONSUMED_RETENTION,
    MAGIC,
    RECORD,
    ConsumedEvidence,
    active,
    decode,
    digest,
    encode,
    identity,
)
from assistant_helpers import event
from test_warning import NOW, indicator


def test_length_delimited_source_identity_and_fixed_size_roundtrip():
    first = replace(event("bc"), source_id="a")
    other = replace(first, id="c", source_id="ab")
    assert digest(first) != digest(other)
    assert digest(first) == digest(replace(first, title="Changed text"))
    entries = dict([identity(first, NOW), identity(other, NOW - timedelta(seconds=1))])
    packed = encode(entries)
    assert len(packed) == len(MAGIC) + 24 * len(entries)
    assert decode(packed, 2) == entries
    assert b"Changed text" not in packed


@pytest.mark.parametrize(
    "data,count",
    [
        (b"unknown", 0),
        (MAGIC + b"x", 0),
        (MAGIC, 1),
        (MAGIC, -1),
        (MAGIC, consumed_evidence.MAX_CONSUMED_PER_RULE + 1),
        (MAGIC + RECORD.pack(b"a" * 16, 0) * 2, 2),
        (MAGIC + RECORD.pack(b"a" * 16, 2**63 - 1), 1),
    ],
)
def test_invalid_records_are_rejected(data, count):
    with pytest.raises(ValueError, match="Invalid consumed evidence"):
        decode(data, count)


def test_expiry_retains_the_inclusive_seven_day_boundary():
    item = replace(event("a"), published_at=NOW)
    entries = dict([identity(item, NOW)])
    end = NOW + CONSUMED_RETENTION
    assert active(entries, end) == entries
    assert active(entries, end + timedelta(microseconds=1)) == {}
    consumed = ConsumedEvidence(frozenset(active(entries, end)))
    rule = replace(
        indicator(threshold=1),
        countries=(),
        categories=(),
        keywords=(),
        severity_floor=0,
        window_minutes=7 * 24 * 60,
    )
    assert warning.evaluate(rule, [item], end, None, consumed=consumed) is None


def test_firing_collection_is_bounded_without_partial_success(monkeypatch):
    monkeypatch.setattr(warning, "MAX_CONSUMED_PER_RULE", 2)
    rule = replace(
        indicator(threshold=1), countries=(), categories=(), keywords=(), severity_floor=0
    )
    firing = warning.evaluate(
        rule, [replace(event(str(i)), published_at=NOW) for i in range(20)], NOW, None
    )
    assert firing is not None and firing.count == 20
    assert firing.consumption_overflow and len(firing.consumed) == 3
    monkeypatch.setattr(consumed_evidence, "MAX_CONSUMED_PER_RULE", 2)
    with pytest.raises(ValueError, match="per-rule bound"):
        encode(dict(firing.consumed))
