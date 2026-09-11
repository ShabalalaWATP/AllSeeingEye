"""Reject ledger rewrites and unsafe counters without duplicating known usage."""

from copy import deepcopy
from uuid import uuid4

import pytest

from ase.application.report_jobs.budget import JobInterrupted
from ase.container.report_job_usage import settled_usage
from report_checkpoint_helpers import reservation
from report_job_helpers import NOW


def transition(**changes):
    row = reservation()
    return {"calls": [row]}, {"calls": [row | {"status": "completed"} | changes]}


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "invalid"},
        {"profile_id": None},
        {"profile_id": "invalid"},
        {"status": "unrecognised"},
        {"reserved_output": 1},
        {"model": "different"},
        {"latency_ms": None},
        {"latency_ms": True},
        {"latency_ms": -1},
        {"latency_ms": float("nan")},
        {"latency_ms": float("inf")},
        {"latency_ms": 3_600_001},
        {"error": "arbitrary raw provider text"},
        {"error": "provider_error"},
    ],
)
def test_invalid_transition_cannot_become_usage(changes):
    before, after = transition(**changes)
    with pytest.raises(JobInterrupted):
        settled_usage(before, after, uuid4(), NOW)


@pytest.mark.parametrize("value", [True, -1, 2**31, "30"])
def test_invalid_provider_counters_remain_unknown(value):
    before, after = transition(prompt_tokens=value, completion_tokens=value)
    row = settled_usage(before, after, uuid4(), NOW)[0]
    assert row.prompt_tokens is row.completion_tokens is None


def test_append_requires_new_reservation_and_settled_entries_are_immutable():
    row = reservation()
    assert settled_usage({}, {"calls": [row]}, uuid4(), NOW) == []
    with pytest.raises(JobInterrupted):
        settled_usage({}, {"calls": [row | {"status": "completed"}]}, uuid4(), NOW)
    before, after = transition()
    assert len(settled_usage(before, after, uuid4(), NOW)) == 1
    changed = deepcopy(after)
    changed["calls"][0]["prompt_tokens"] = 1
    with pytest.raises(JobInterrupted):
        settled_usage(after, changed, uuid4(), NOW)


@pytest.mark.parametrize("calls", [None, {}, [None], [{"id": 1}], [reservation()] * 2])
def test_malformed_or_duplicated_ledger_is_rejected(calls):
    with pytest.raises(JobInterrupted):
        settled_usage({}, {"calls": calls}, uuid4(), NOW)


def test_reservation_cannot_be_changed_or_removed():
    row = reservation()
    for changed in ([], [row | {"prompt_tokens": 1}], [reservation()]):
        with pytest.raises(JobInterrupted):
            settled_usage({"calls": [row]}, {"calls": changed}, uuid4(), NOW)
