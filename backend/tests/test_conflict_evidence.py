"""Conflict summaries must distinguish evidence, incidents and coverage gaps."""

from datetime import timedelta

from ase.domain.conflict_evidence import (
    canonical_report_url,
    casualties,
    evidence_groups,
    occurrence_time,
)
from ase.domain.events import Category
from ase.domain.trackers import conflict_card
from feeds_helpers import NOW, make_event
from tracker_helpers import UKRAINE


def report(key="a", subtype="fight", **changes):
    return make_event(key, category=Category.CONFLICT, subtype=subtype).with_changes(**changes)


def test_protests_and_posture_are_not_fighting_and_unknown_deaths_are_not_zero():
    card = conflict_card(
        UKRAINE, [report(), report("b", "protest"), report("c", "force_posture")], NOW
    )
    assert card.activity.last_7d == 1
    assert card.other_activity_7d == 2
    assert card.fatalities_7d is None


def test_new_reporting_of_old_event_does_not_create_recent_fighting():
    event = report(attributes={"occurrence_start": (NOW - timedelta(days=40)).isoformat()})
    assert conflict_card(UKRAINE, [event], NOW).activity.last_7d == 0


def test_missing_machine_event_date_is_unknown_not_today():
    event = report(
        source_id="gdelt_events",
        attributes={"conflict_screening": "llm", "conflict_relevance": "armed_conflict"},
    )
    card = conflict_card(UKRAINE, [event], NOW)
    assert card.activity.last_7d == 0
    assert card.unknown_date_reports == 1


def test_duplicate_evidence_does_not_double_casualty_count():
    attributes = {"occurrence_start": NOW.isoformat(), "fatalities": 4}
    first = report(attributes=attributes)
    repeated = report("b", url=first.url, attributes=attributes)
    card = conflict_card(UKRAINE, [first, repeated], NOW)
    assert card.activity.last_7d == 1
    assert card.fatalities_7d == 4
    assert card.collapsed_reports_7d == 1


def test_transport_and_weather_are_not_context_reporting():
    events = [make_event("plane", category=Category.AVIATION), make_event("weather")]
    assert conflict_card(UKRAINE, events, NOW).reporting_7d == 0


def test_ranges_unknown_zero_and_disputed_estimates_are_distinct():

    first = report(
        attributes={
            "origin_dataset": "test",
            "incident_id": "1",
            "reported_fatalities_low": 2,
            "reported_fatalities_high": 5,
        }
    )
    duplicate = report(
        "b", attributes={"origin_dataset": "test", "incident_id": "1", "fatalities": 3}
    )
    uncertain = report(
        "c", attributes={"reported_fatalities_best": 0, "fatalities_uncertain_zero": True}
    )
    result = casualties(evidence_groups([first, duplicate, uncertain]))
    assert (result.lower, result.upper, result.unknown_incidents, result.disputed_incidents) == (
        2,
        5,
        1,
        1,
    )
    assert casualties([(report(attributes={"fatalities": 0}),)]).lower == 0


def test_bad_dates_and_future_reports_cannot_be_recent_violence():

    assert occurrence_time(report(attributes={"event_day": "invalid"})) is None
    assert occurrence_time(report(attributes={"event_day": "20260901"})).day == 1
    future = report(attributes={"occurrence_start": (NOW + timedelta(days=1)).isoformat()})
    card = conflict_card(UKRAINE, [future], NOW)
    assert card.activity.last_7d == 0 and card.latest is None


def test_url_grouping_is_conservative_and_tracking_parameters_do_not_duplicate():

    first = report(url="https://example.com/article?a=1&utm_source=x#section")
    duplicate = report("b", url="https://example.com/article?a=1")
    separate = report("c", subtype="strike", url=duplicate.url)
    assert [len(group) for group in evidence_groups([first, duplicate, separate, first])] == [2, 1]
    for url in (None, "file:///private", "https://user:secret@example.com", "https://["):
        assert canonical_report_url(url) is None


def test_invalid_fatalities_never_enter_total():

    for value in (True, -1, 2.5, float("nan"), float("inf"), "3", None):
        assert casualties([(report(attributes={"fatalities": value}),)]).lower is None


def test_provider_point_estimate_with_missing_bounds_is_preserved():
    event = report(
        attributes={
            "reported_fatalities_best": 4,
            "reported_fatalities_low": None,
            "reported_fatalities_high": None,
        }
    )
    result = casualties([(event,)])
    assert result.lower == result.upper == 4


def test_imprecise_dates_and_unrelated_humanitarian_reports_do_not_inflate_activity():
    for attrs in (
        {"date_precision": 2},
        {"date_precision": 3},
        {"occurrence_end": (NOW + timedelta(days=1)).isoformat()},
    ):
        event = report(
            source_id="acled_events", attributes={"occurrence_start": NOW.isoformat(), **attrs}
        )
        assert occurrence_time(event) is None
        assert conflict_card(UKRAINE, [event], NOW).activity.last_7d == 0
    irrelevant = make_event(
        "health", category=Category.HUMANITARIAN, title="Routine vaccination programme"
    )
    assert conflict_card(UKRAINE, [irrelevant], NOW).reporting_7d == 0
