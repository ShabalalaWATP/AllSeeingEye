"""Preview, creation, follow-up and provider limits agree on historical scope."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ase.api.schemas_reports import ReportCreateIn
from ase.api.schemas_research_plan import ResearchPlanIn
from ase.application.reports.followup_scope import require_followup_scope
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import template_for
from ase.domain.errors import InvalidRequest
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import ResearchMode
from ase.domain.research_scope import MAX_RESEARCH_HOURS, validate_research_interval
from test_research_collection import NOW, QUERY


def report(**kwargs):
    return ReportCreateIn(
        template="ask",
        question="What changed?",
        research_mode="quick",
        **kwargs,
    )


def preview(**kwargs):
    return ResearchPlanIn(question="What changed?", **kwargs)


@pytest.mark.parametrize("days", [1, 15, 180, 365, 730])
def test_fixed_historical_range_is_supported_consistently(days):
    since = NOW - timedelta(days=days)
    query = preview(since=since, until=NOW).to_query()
    request = report(research_since=since, research_until=NOW).to_request()
    assert query.since == request.research_since == since
    assert query.until == request.research_until == NOW
    assert request.window_hours is None
    assert report(window_hours=days * 24).to_request().window_hours == days * 24


@pytest.mark.parametrize(
    "delta", [timedelta(0), timedelta(seconds=-1), timedelta(days=730, seconds=1)]
)
def test_nonpositive_and_over_two_year_ranges_rejected_by_all_boundaries(delta):
    since = NOW - delta
    with pytest.raises(ValidationError):
        preview(since=since, until=NOW)
    with pytest.raises(ValidationError):
        report(research_since=since, research_until=NOW)
    with pytest.raises(ValueError):
        replace(QUERY, since=since, until=NOW)
    with pytest.raises(ValueError):
        ReportRequest(
            "ask", research_mode=ResearchMode.QUICK, research_since=since, research_until=NOW
        )


def test_rolling_and_explicit_intervals_cannot_be_combined():
    with pytest.raises(ValidationError, match="fixed research interval or a rolling window"):
        report(window_hours=24, research_since=QUERY.since, research_until=NOW)
    with pytest.raises(ValidationError):
        report(window_hours=MAX_RESEARCH_HOURS + 1)
    with pytest.raises(ValueError):
        ReportRequest("ask", window_hours=MAX_RESEARCH_HOURS + 1)


def test_research_dates_need_timezones_and_cannot_end_in_future():
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    with pytest.raises(ValidationError, match="future"):
        report(research_since=NOW, research_until=tomorrow)
    with pytest.raises(ValidationError, match="future"):
        preview(since=NOW, until=tomorrow)
    with pytest.raises(ValidationError):
        preview(since=QUERY.since.replace(tzinfo=None), until=NOW)
    with pytest.raises(ValueError, match="future"):
        validate_research_interval(QUERY.since, NOW + timedelta(hours=1), now=NOW)


def test_recorded_project_year_policy_stays_distinct():
    since = NOW - timedelta(days=3650)
    query = preview(since=since, until=NOW, time_basis="recorded_time").to_query()
    request = report(
        research_since=since,
        research_until=NOW,
        research_time_basis="recorded_time",
    ).to_request()
    assert query.effective_time_basis is request.effective_time_basis is EvidenceTimeBasis.RECORDED
    with pytest.raises(ValueError):
        replace(query, since=NOW - timedelta(days=31 * 366))


def test_followup_retains_exact_countries_and_historical_interval():
    parent = report(
        countries=["UA", "PL"],
        research_since=NOW - timedelta(days=300),
        research_until=NOW,
    ).to_request()
    scope = report_scope(parent, template_for("ask"))
    require_followup_scope(scope, replace(parent, question="What remains uncertain?"))
    require_followup_scope(scope, replace(parent, country_isos=("PL", "UA")))
    with pytest.raises(InvalidRequest, match="countries"):
        require_followup_scope(scope, replace(parent, country_isos=()))
    with pytest.raises(InvalidRequest, match="fixed interval"):
        require_followup_scope(scope, replace(parent, research_since=NOW - timedelta(days=1)))
    with pytest.raises(InvalidRequest, match="fixed interval"):
        require_followup_scope(scope, replace(parent, research_since=None, research_until=None))


def test_rolling_followup_refreshes_current_window_without_turning_it_into_fixed_history():
    parent = report(countries=["UA", "PL"], window_hours=24).to_request()
    scope = report_scope(parent, template_for("ask"))
    require_followup_scope(scope, replace(parent, question="What changed since then?"))
    with pytest.raises(InvalidRequest, match="fixed interval"):
        require_followup_scope(
            scope,
            replace(parent, window_hours=None, research_since=QUERY.since, research_until=NOW),
        )
    with pytest.raises(InvalidRequest, match="invalid research scope"):
        require_followup_scope({"countries": "GB"}, parent)
    with pytest.raises(InvalidRequest, match="invalid research scope"):
        require_followup_scope({"research_since": "invalid"}, parent)


@pytest.mark.parametrize(
    "scope",
    [
        {"research_since": "2025-01-01T00:00:00+00:00"},
        {"research_since": "2025-01-01", "research_until": "2025-01-02"},
        {
            "research_since": "2025-01-02T00:00:00+00:00",
            "research_until": "2025-01-01T00:00:00+00:00",
        },
    ],
)
def test_malformed_frozen_intervals_fail_closed_before_reusing_evidence(scope):
    with pytest.raises(InvalidRequest, match="invalid research scope"):
        require_followup_scope(scope, ReportRequest("ask"))
