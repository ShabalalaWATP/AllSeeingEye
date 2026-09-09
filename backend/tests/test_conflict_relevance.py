"""Machine coding and ambiguous news must not create current conflict incidents."""

import pytest

from ase.domain.conflict_evidence import is_conflict_context, is_violence
from ase.domain.conflict_relevance import is_admitted_conflict
from ase.domain.events import Category, Point
from ase.domain.trackers import conflict_card
from feeds_helpers import NOW, make_event
from tracker_helpers import UKRAINE

ACCIDENT = "£1.2m fines after Surrey construction worker buried alive in trench collapse"


def machine(relevance=None, **changes):
    attrs = {"event_code": "173", "occurrence_start": NOW.isoformat()}
    if relevance:
        attrs |= {"conflict_screening": "llm", "conflict_relevance": relevance}
    return make_event(
        "accident",
        category=Category.CONFLICT,
        source_id="gdelt_events",
        subtype="fight",
        title=ACCIDENT,
    ).with_changes(attributes=attrs, **changes)


@pytest.mark.parametrize("relevance", [None, "unrelated", "uncertain", "context", "invalid"])
def test_unreviewed_or_rejected_machine_report_cannot_count_as_conflict(relevance):
    event = machine(relevance)
    assert not is_admitted_conflict(event) and not is_violence(event)
    card = conflict_card(UKRAINE, [event], NOW)
    assert card.activity.last_7d == 0 and card.other_activity_7d == 0
    assert card.latest is None and card.top is None and card.fatalities_7d is None


@pytest.mark.parametrize("relevance", ["civil_unrest", "military_activity"])
def test_screened_protest_or_drill_is_not_counted_as_armed_violence(relevance):
    event = machine(relevance)
    assert is_admitted_conflict(event) and not is_violence(event)
    assert conflict_card(UKRAINE, [event], NOW).other_activity_7d == 1


def test_screened_armed_report_preserves_grades_and_provider_basis():
    event = machine("armed_conflict")
    assert is_violence(event)
    assert conflict_card(UKRAINE, [event], NOW).activity.last_7d == 1
    assert event.attributes["event_code"] == "173"


def test_rejected_news_context_and_sensor_metadata_do_not_inflate_conflict_reporting():
    news = make_event(
        "news", category=Category.NEWS, title="Industrial strike after trench accident"
    )
    assert is_conflict_context(news)
    rejected = news.with_changes(
        attributes={"conflict_screening": "llm", "conflict_relevance": "unrelated"}
    )
    assert not is_conflict_context(rejected)
    sensor = machine("armed_conflict").with_changes(category=Category.AVIATION)
    assert not is_conflict_context(sensor) and not is_admitted_conflict(sensor)


def test_curated_tracker_detail_excludes_pending_and_rejected_media(container):
    for index, relevance in enumerate((None, "unrelated", "context", "armed_conflict")):
        container.store.upsert(
            [machine(relevance, id=str(index), point=Point(36.2, 49.9), country_iso="UA")]
        )
    result = container.trackers().conflict_detail("ukraine")
    assert {event.id for event in result.events} == {"2", "3"}
