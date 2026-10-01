"""Polling metadata is derived separately from the original bounded checkpoint."""

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from ase.adapters.persistence.report_job_codec import payload_columns, with_summary
from ase.adapters.persistence.report_job_projection import polling_payload
from ase.domain.report_jobs import MAX_JOB_SUMMARY_BYTES, canonical_job_payload
from report_job_helpers import job


@pytest.mark.parametrize(
    "scope,expected",
    [
        ({"origin": origin, "research_focus": "media"}, origin)
        for origin in ("research", "subscription", "geolocation", "briefing")
    ]
    + [
        ({"research_focus": "media"}, "geolocation"),
        ({"origin": "unknown", "research_focus": "media"}, "geolocation"),
        ({"origin": [], "research_focus": "media"}, "geolocation"),
        ({"origin": "unknown"}, "research"),
        ({}, "research"),
        (None, "research"),
        ([], "research"),
    ],
)
def test_origin_comes_from_frozen_scope_without_rewriting_checkpoint(scope, expected):
    payload = {
        "schema_version": 1,
        "input": {"scope": scope},
        "summary": {"origin": "spoofed", "nested": {"count": 1}},
    }
    original = deepcopy(payload)
    encoded = canonical_job_payload(payload)
    columns = payload_columns(payload)
    assert columns["summary"] == {"origin": expected, "nested": {"count": 1}}
    assert columns["payload"].encode() == encoded
    assert columns["payload_bytes"] == len(encoded)
    assert columns["payload_sha256"] == hashlib.sha256(encoded).hexdigest()
    columns["summary"]["nested"]["count"] = 2
    assert payload == original


@pytest.mark.parametrize("frozen", [None, [], "legacy"])
def test_missing_or_legacy_input_keeps_research_classification(frozen):
    assert payload_columns({"schema_version": 1, "input": frozen})["summary"] == {
        "origin": "research"
    }


def full_summary(**extra):
    summary = {"padding": "", **extra}
    summary["padding"] = "x" * (MAX_JOB_SUMMARY_BYTES - len(json.dumps(summary).encode()))
    assert len(json.dumps(summary).encode()) == MAX_JOB_SUMMARY_BYTES
    return summary


@pytest.mark.parametrize("origin", ["research", "subscription", "geolocation", "briefing"])
def test_derived_metadata_does_not_reduce_original_summary_allowance(origin):
    payload = {
        "schema_version": 1,
        "input": {"scope": {"origin": origin}},
        "summary": full_summary(),
    }
    encoded = canonical_job_payload(payload)
    columns = payload_columns(payload)
    assert columns["payload"].encode() == encoded
    assert columns["summary"] == {**payload["summary"], "origin": origin}
    assert len(json.dumps(columns["summary"]).encode()) > MAX_JOB_SUMMARY_BYTES
    assert polling_payload(columns["summary"])["summary"] == columns["summary"]


def test_projection_cannot_hide_an_invalid_original_checkpoint_by_replacing_origin():
    payload = {"schema_version": 1, "summary": full_summary(origin="x" * 100)}
    payload["summary"]["padding"] += "x"
    with pytest.raises(ValueError):
        payload_columns(payload)


@pytest.mark.parametrize("origin", [True, 1, [], {}, "unknown", "x" * MAX_JOB_SUMMARY_BYTES])
def test_thin_codec_rejects_unrecognised_or_unbounded_derived_origin(origin):
    with pytest.raises(ValueError):
        polling_payload({"origin": origin})


def test_thin_codec_retains_original_json_bounds_and_breaks_mutable_aliases():
    summary = {"nested": {"count": 1}, "origin": "briefing"}
    view = polling_payload(summary)
    view["summary"]["nested"]["count"] = 2
    assert summary["nested"]["count"] == 1
    too_large = full_summary()
    too_large["padding"] += "x"
    with pytest.raises(ValueError):
        polling_payload({**too_large, "origin": "research"})
    with pytest.raises(ValueError):
        polling_payload({"origin": "research", "password": "private"})
    nested = {}
    for _ in range(50):
        nested = {"child": nested}
    with pytest.raises(ValueError, match="too complex"):
        polling_payload({"origin": "research", "nested": nested})


@pytest.mark.parametrize("changes", [{"revision": 0}, {"status": "unknown"}, {"title": ""}])
def test_thin_codec_still_validates_all_job_metadata(changes):
    row = SimpleNamespace(**(asdict(job()) | changes))
    with pytest.raises(ValueError):
        with_summary(row, {"origin": "research"})
