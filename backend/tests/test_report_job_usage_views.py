"""Active reservations are not warnings; lost or failed unconfirmed usage still is."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.application.report_jobs.views import job_view, refresh_summary
from report_job_helpers import NOW, job
from report_job_service_helpers import call
from test_report_job_views import payload


def progress(status, calls):
    value = payload()
    value["calls"] = calls
    refresh_summary(value)
    lease = (
        {"lease_token": uuid4(), "lease_until": NOW + timedelta(minutes=5)}
        if status == "running"
        else {}
    )
    return job(status=status, payload=value, **lease)


@pytest.mark.parametrize(
    "status", ["queued", "running", "paused", "failed", "completed", "needs_review"]
)
def test_inflight_reservation_warns_only_once_the_job_is_no_longer_active(status):
    value = progress(status, [call()])
    result = job_view(value)
    assert result["usage"]["uncertain_calls"] == (0 if status in {"queued", "running"} else 1)
    assert result["usage"]["output_tokens"] == 32000
    assert value.payload["summary"]["usage"]["uncertain_calls"] == 0
    assert value.payload["summary"]["in_flight_calls"] == 1
    assert "in_flight_calls" not in result["usage"] and "in_flight_calls" not in result
    thin = replace(value, payload={"schema_version": 1, "summary": value.payload["summary"]})
    assert job_view(thin, detail=False)["usage"] == result["usage"]


@pytest.mark.parametrize("status", ["running", "paused"])
def test_existing_uncertain_outcomes_remain_visible_during_a_new_call(status):
    value = progress(status, [call("uncertain"), call()])
    assert job_view(value)["usage"]["uncertain_calls"] == (1 if status == "running" else 2)
    assert job_view(value)["usage"]["output_tokens"] == 64000
    assert value.payload["summary"]["usage"]["uncertain_calls"] == 1


@pytest.mark.parametrize(
    "completion,unknown",
    [(None, True), (False, True), (-1, True), (2**31, True), (0, False), (500, False)],
)
def test_failed_calls_warn_only_when_the_output_usage_is_unknown(completion, unknown):
    value = progress("running", [call("failed", completion_tokens=completion)])
    result = job_view(value)["usage"]
    assert result["uncertain_calls"] == int(unknown)
    assert result["output_tokens"] == (32000 if unknown else completion)
    assert value.payload["summary"]["in_flight_calls"] == 0


def test_three_interrupted_or_unmetered_calls_remain_three_after_resume():
    calls = [call("uncertain"), call("uncertain"), call("failed", error="provider_error")]
    for state in ("queued", "running", "paused"):
        result = job_view(progress(state, calls))["usage"]
        assert result["uncertain_calls"] == 3 and result["output_tokens"] == 96000


def test_completed_call_with_known_usage_does_not_raise_a_warning():
    result = job_view(progress("completed", [call("completed", completion_tokens=500)]))["usage"]
    assert result["uncertain_calls"] == 0 and result["output_tokens"] == 500


def test_legacy_summary_without_new_internal_counter_is_not_counted_twice():
    value = progress("paused", [call("uncertain")])
    value.payload["summary"].pop("in_flight_calls", None)
    assert job_view(value)["usage"]["uncertain_calls"] == 1


@pytest.mark.parametrize("status,expected", [("running", 1), ("paused", 2)])
def test_legacy_detail_recomputes_flags_from_ledger_without_rewriting_saved_summary(
    status, expected
):
    value = progress(status, [call(), call("failed", completion_tokens=None)])
    summary = value.payload["summary"]
    summary.pop("in_flight_calls")
    summary["usage"]["uncertain_calls"] = 0
    result = job_view(value)["usage"]
    assert result["uncertain_calls"] == expected and result["output_tokens"] == 64000
    assert "in_flight_calls" not in summary and summary["usage"]["uncertain_calls"] == 0
