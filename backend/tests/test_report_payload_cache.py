"""Validated checkpoint bytes never retain a caller's mutable JSON tree."""

import math

import pytest

from ase.adapters.persistence import report_job_codec
from ase.adapters.persistence.report_job_codec import PayloadCache
from ase.domain.report_jobs import canonical_job_payload


def payload(value="original"):
    return {
        "schema_version": 1,
        "nested": [{"items": [value, None, True, False, 1, 1.0, -0.0, "é🚢"]}],
    }


def test_miss_hit_and_independent_caches_return_fresh_nested_json():
    expected = payload()
    encoded = canonical_job_payload(expected)
    cache = PayloadCache()
    first = cache.decode(encoded)
    first["nested"][0]["items"].append({"transient": []})
    first["nested"].append({"items": ["changed"]})
    second = cache.decode(encoded)
    assert second == expected
    second["nested"][0]["items"][0] = "also changed"
    third = cache.decode(encoded)
    independent = PayloadCache().decode(encoded)
    assert third == independent == expected
    assert third["nested"] is not independent["nested"]
    items = third["nested"][0]["items"]
    assert [type(value) for value in items] == [str, type(None), bool, bool, int, float, float, str]
    assert math.copysign(1, items[6]) == -1


@pytest.mark.parametrize(
    "invalid",
    [
        b"not JSON",
        b'{ "schema_version": 1}',
        b'{"schema_version":2}',
        b'{"schema_version":true}',
        b'{"schema_version":1,"value":NaN}',
        b'{"schema_version":1,"value":1,"value":2}',
        b'{"password":"forbidden","schema_version":1}',
    ],
)
def test_invalid_replacement_cannot_poison_last_validated_bytes(monkeypatch, invalid):
    first = canonical_job_payload(payload("first"))
    final = canonical_job_payload(payload("final"))
    canonical = report_job_codec.canonical_job_payload
    validations = []

    def validate(value):
        validations.append(value)
        return canonical(value)

    monkeypatch.setattr(report_job_codec, "canonical_job_payload", validate)
    cache = PayloadCache()
    assert cache.decode(first) == payload("first")
    with pytest.raises(ValueError):
        cache.decode(invalid)
    count = len(validations)
    assert cache.decode(first) == payload("first")
    assert len(validations) == count
    assert cache.decode(final) == payload("final")
    assert len(validations) == count + 1
    assert cache.decode(first) == payload("first")
    assert len(validations) == count + 2
