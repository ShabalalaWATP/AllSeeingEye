"""Local subject requests cannot spend evidence slots on unrelated country context."""

from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.production import Producer
from ase.application.reports.production_checkpoint import ProductionSnapshot
from ase.application.reports.production_selection import plan_for_job, select_for_job
from ase.application.reports.production_types import Totals
from ase.application.reports.request import ReportRequest
from ase.application.reports.selection import Selection
from ase.domain.direction import Direction
from ase.domain.events import Category, Event
from ase.domain.research import ResearchFocus, ResearchMode, ResearchQuery
from ase.domain.research_area import direct_area_from_geometry
from feeds_helpers import NOW, make_event
from report_job_snapshot_helpers import fixture_evidence, fixture_job

QUESTION = "I need an update on Drone and Missile Attacks in Kyiv"


def event(key: str, title: str, category: Category = Category.CONFLICT) -> Event:
    return make_event(key, title=title, source_id=key, country_iso="UA", category=category)


def selected_events(question: str, events: tuple[Event, ...], **kwargs: object) -> set[str]:
    request = ReportRequest(
        "ask", question=question, country_iso="UA", research_mode=ResearchMode.QUICK
    )
    job = fixture_job(request)
    store = InMemoryEventStore()
    store.upsert(events)
    result = select_for_job(store, {}, job, None, **kwargs)  # type: ignore[arg-type]
    return {item.event_id for item in result.items}


def test_targeted_request_excludes_unrelated_country_context_before_reranking() -> None:
    relevant = (
        event("attack", "Kyiv reports a drone interception"),
        event("contrary", "Officials deny any missile attacks in Kyiv"),
        event("consequence", "Kyiv hospital evacuated after overnight strike", Category.DISASTER),
        event("relief", "Emergency aid after Kyiv drone damage", Category.HUMANITARIAN),
        replace(event("translated", "Original source headline"), title_en="Kyiv missile damage"),
    )
    unrelated = (
        event("fire", "NOAA-20 thermal anomaly", Category.DISASTER),
        event("loss", "Ukraine national military equipment loss totals"),
        event("protest", "Protest in Ukraine", Category.POLITICAL),
        event("assessment", "Russian offensive campaign assessment across Ukraine"),
        event("elsewhere", "Missile and drone attacks in Odesa"),
        event("same-city", "Kyiv river flood warning", Category.DISASTER),
        event("substring", "Kyivstar drone delivery demonstration"),
    )
    request = ReportRequest(
        "ask", question=QUESTION, country_iso="UA", research_mode=ResearchMode.QUICK
    )
    job = fixture_job(request)
    store = InMemoryEventStore()
    store.upsert((*relevant, *unrelated))
    query = ResearchQuery(
        QUESTION,
        job.period_from,
        job.period_to,
        country_iso="UA",
        terms=("Kyiv drone attack", "Kyiv missile strike", "Kiev drone attack"),
    )
    direction = Direction(QUESTION, categories=(Category.CONFLICT, Category.DISASTER))
    plan = plan_for_job(store, job, direction, runtime_query=query)
    assert {item.id for item in plan.rerank_candidates()} == {item.id for item in relevant}
    selected = select_for_job(
        store,
        {},
        job,
        direction,
        runtime_query=query,
        similarity={item.id: 1.0 for item in unrelated},
    )
    assert {item.event_id for item in selected.items} == {item.id for item in relevant}
    assert selected.flagged == 0  # Irrelevance is not an injection-safety finding.


def test_targeted_empty_evidence_does_not_fall_back_to_country_context() -> None:
    assert selected_events(QUESTION, (event("unrelated", "Ukraine national loss totals"),)) == set()


def test_runtime_query_cannot_replace_the_original_locality() -> None:
    job = fixture_job(ReportRequest("ask", question=QUESTION, research_mode=ResearchMode.QUICK))
    query = ResearchQuery(
        "Revised search", job.period_from, job.period_to, terms=("Odesa drone attack",)
    )
    kyiv = event("kyiv", "Drone intercepted above Kyiv")
    odesa = event("odesa", "Odesa drone attack")
    assert selected_events(QUESTION, (kyiv, odesa), runtime_query=query) == {kyiv.id}


def test_locality_rule_is_not_specific_to_one_city_and_matches_word_forms() -> None:
    relevant = event("relevant", "New York prepares for a flood")
    elsewhere = event("elsewhere", "Floods near York")
    scattered = event("scattered", "New flood barriers installed in York")
    assert selected_events("Update on floods in New York", (relevant, elsewhere, scattered)) == {
        relevant.id
    }


@pytest.mark.parametrize(
    "question",
    (
        "I need an update on Ukraine",
        "Give me a general briefing in Ukraine",
        "Give me a general briefing in Kyiv",
        "Latest news in Kyiv",
        "Latest headlines in Kyiv",
        "Latest stories in Kyiv",
        "Update on inflation in UK",
        "Update on inflation in GB",
        "Update on inflation in USA",
        "Update on inflation in France",
        "Summarise Ukraine conflict in English",
        "Summarise Ukraine conflict in Ukrainian",
        "Report the situation in the last 24 hours",
        "Report the situation in 2026",
        "Report the situation at present",
        "Report the situation in relation to air defence",
        "Report the situation in the Last Week",
        "Report the situation in Relation To Air Defence",
        "An update on attacks in kyiv",
        "An update on attacks in Kyiv and Odesa",
    ),
)
def test_general_or_ambiguous_requests_preserve_context(question: str) -> None:
    rows = (event("one", "Countrywide reporting"), event("two", "Thermal anomaly"))
    assert selected_events(question, rows) == {item.id for item in rows}


@pytest.mark.parametrize("focus", (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA))
def test_explicit_private_input_is_not_filtered_by_a_public_locality_rule(
    focus: ResearchFocus,
) -> None:
    request = ReportRequest("ask", question=QUESTION, research_mode=ResearchMode.QUICK)
    job = fixture_job(replace(request, research_focus=focus))
    supplied = event("supplied", "Uncaptioned supplied material")
    store = InMemoryEventStore()
    store.upsert((supplied,))
    assert [row.event_id for row in select_for_job(store, {}, job, None).items] == [supplied.id]


def test_explicit_area_keeps_provider_admitted_evidence() -> None:
    area = direct_area_from_geometry(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[30, 50], [31, 50], [31, 51], [30, 51], [30, 50]]],
                    },
                }
            ],
        }
    )
    request = ReportRequest(
        "ask", question=QUESTION, research_mode=ResearchMode.QUICK, research_area=area
    )
    job = fixture_job(request)
    admitted = event("admitted", "Provider observation inside the selected area")
    store = InMemoryEventStore()
    store.upsert((admitted,))
    assert [row.event_id for row in select_for_job(store, {}, job, None).items] == [admitted.id]


def test_explicitly_reused_frozen_evidence_is_not_rewritten() -> None:
    frozen = fixture_evidence()
    job = fixture_job(ReportRequest("ask", question=QUESTION, research_mode=ResearchMode.QUICK))
    job = replace(job, reused_evidence=(frozen,))
    selected = select_for_job(InMemoryEventStore(), {}, job, None)
    assert selected.items == (frozen,)


def test_source_summary_can_establish_relevance_but_no_place_alias_is_invented() -> None:
    summary = replace(
        event("summary", "Emergency response"), summary="Kyiv's residents report drone damage."
    )
    alternative = event("alternative", "Kiev drone attack")
    assert selected_events(QUESTION, (summary, alternative)) == {summary.id}


def test_targeted_relevance_cannot_override_country_or_period() -> None:
    current = event("current", "Kyiv missile attack")
    outside_country = replace(event("outside", current.title), country_iso="GB")
    outside_period = replace(event("old", current.title), published_at=NOW - timedelta(days=90))
    assert selected_events(QUESTION, (current, outside_country, outside_period)) == {current.id}


def test_public_locality_gate_does_not_change_non_research_reports() -> None:
    request = ReportRequest("ask", question=QUESTION, country_iso="UA")
    job = fixture_job(request)
    store = InMemoryEventStore()
    retained = event("retained", "Country context")
    store.upsert((retained,))
    assert [row.event_id for row in select_for_job(store, {}, job, None).items] == [retained.id]


async def test_paused_targeted_job_reuses_its_frozen_packet_without_reselection() -> None:
    job = fixture_job(ReportRequest("ask", question=QUESTION, research_mode=ResearchMode.QUICK))
    frozen = Selection((fixture_evidence(),), flagged=0, considered=1)
    snapshot = ProductionSnapshot(frozen, Direction(QUESTION), None, None, Totals())
    checkpoints = SimpleNamespace(
        load_collection=AsyncMock(return_value=snapshot),
        save_collection=AsyncMock(side_effect=AssertionError("Frozen packet must not change")),
        section_checkpoints=AsyncMock(),
    )
    gateway = AsyncMock()
    producer = Producer(
        store=InMemoryEventStore(),
        source_profiles={},
        cipher=Mock(),
        gateway=gateway,
        usage=AsyncMock(),
    )

    def reached_drafting(*args: object, **kwargs: object) -> None:
        assert args[7] == frozen.items
        raise RuntimeError("Frozen packet reached drafting")

    with (
        patch(
            "ase.application.reports.production.select_for_job",
            side_effect=AssertionError("Resumption must not reselect evidence"),
        ),
        patch("ase.application.reports.production.draft_sections", side_effect=reached_drafting),
        pytest.raises(RuntimeError, match="Frozen packet reached drafting"),
    ):
        await producer.produce(job, AsyncMock(return_value=job.profile), checkpoints=checkpoints)
    gateway.complete.assert_not_called()
    checkpoints.save_collection.assert_not_called()
