"""Explicit geography, topic alternatives and source classification semantics."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.application.assistant.intent import interpret_question
from ase.application.assistant.sources import event_source
from ase.domain.assistant import AssistantQuestion
from ase.domain.events import Category
from assistant_helpers import NOW, event
from test_assistant_retrieval import retrieval


@pytest.mark.parametrize(
    ("text", "countries"),
    [
        ("South Sudan", ("SS",)),
        ("Northern Ireland", ()),
        ("Democratic People's Republic of Korea", ("KP",)),
        ("People's Republic of China", ("CN",)),
        ("Ukraine and Russia", ("RU", "UA")),
    ],
)
def test_longer_distinct_countries_do_not_widen_scope(text, countries):
    assert interpret_question(text).countries == countries


@pytest.mark.parametrize("text", ["london flights", "flights over london", "ships near atlantis"])
def test_lowercase_place_without_support_never_fills_with_global_traffic(text):
    intent = interpret_question(text)
    for category in (Category.AVIATION, Category.MARITIME):
        source = event_source(event(category=category, title="Public transponder observation"))
        assert not intent.accepts(category.value, source)


def test_answer_formatting_clauses_do_not_become_required_evidence_entities():
    text = (
        "Summarise the earthquake observations available in the retained map sources. "
        "Give two brief observations and one limitation. "
        "Do not claim this is a complete worldwide earthquake list."
    )
    intent = interpret_question(text)
    source = event_source(event(title="M4.0 earthquake, Japan"))
    assert intent.topics == ("earthquake",) and not intent.anchors
    assert intent.accepts("disaster", source)
    assert not intent.accepts("maritime", event_source(event(category=Category.MARITIME)))


@pytest.mark.parametrize(
    "text",
    [
        "Any flights over london? Keep the answer concise.",
        "Are there ships? Include vessels near atlantis. Give two brief observations.",
        "Summarise earthquakes. What happened in london? Do not invent facts.",
    ],
)
def test_later_substantive_location_clauses_remain_required(text):
    intent = interpret_question(text)
    for category in (Category.AVIATION, Category.MARITIME, Category.DISASTER):
        source = event_source(event(category=category, title="Public observation in Japan"))
        assert not intent.accepts(category.value, source)


@pytest.mark.parametrize(
    ("text", "topics", "countries", "anchors"),
    [
        (
            "What earthquakes have been reported? Keep it short and explain the limitations.",
            ("earthquake",),
            (),
            (),
        ),
        (
            "Show me recent earthquakes in Japan, with citations and a short answer.",
            ("earthquake",),
            ("JP",),
            (),
        ),
        (
            "Show me recent earthquakes in Japan with citations and a short answer.",
            ("earthquake",),
            ("JP",),
            (),
        ),
        ("What is happening near London? Please answer in two bullet points.", (), (), ("london",)),
        (
            "Are any ships near Taiwan? Do not make assumptions about their mission.",
            ("maritime",),
            ("TW",),
            (),
        ),
        ("Earthquakes in Japan. Do not assume Iran caused them.", ("earthquake",), ("JP",), ()),
        ("Give two brief observations near london.", (), (), ("london",)),
        ("Summarise earthquakes. Give two observations in Japan.", ("earthquake",), ("JP",), ()),
        ("Show flights. Keep the answer focused on London.", ("aviation",), (), ("london",)),
    ],
)
def test_presentation_clauses_preserve_only_the_requested_subjects(
    text, topics, countries, anchors
):
    intent = interpret_question(text)
    assert (intent.topics, intent.countries, intent.anchors) == (topics, countries, anchors)


def test_long_formatting_preamble_does_not_consume_the_place_term_budget():
    text = "Please answer in two bullet points " + "carefully " * 40 + ". Flights near london."
    intent = interpret_question(text)
    assert intent.topics == ("aviation",) and intent.anchors == ("london",)


@pytest.mark.parametrize(
    "text",
    [
        "Show flights. Do not include Iran.",
        "Non-military flights",
        "Summarise earthquakes. Give two observations covering Japan.",
        "Show flights. Keep the answer London-focused.",
    ],
)
async def test_unsupported_exclusions_request_clarification_before_search(container, user, text):
    container.store.upsert((event(category=Category.AVIATION, country="IR"),))
    result = await retrieval(container).collect(user, AssistantQuestion(text))
    assert not result.sources and result.candidate_count == 0 and result.clarification


async def test_type35_ship_and_military_conflict_are_not_lost_to_aircraft_only_rules(
    container, user
):
    container.store.upsert(
        [
            event(
                "type35",
                category=Category.MARITIME,
                title="Vessel A",
                attributes={"ship_type_code": 35},
            ),
            event("report", category=Category.CONFLICT, title="Military units reported at border"),
        ]
    )
    service = retrieval(container)
    ships = await service.collect(user, AssistantQuestion("Military ships"))
    conflicts = await service.collect(user, AssistantQuestion("Military conflicts"))
    assert [row.record_id for row in ships.sources] == ["type35"]
    assert [row.record_id for row in conflicts.sources] == ["report"]


async def test_newest_records_survive_provider_quota(container, user):
    container.store.upsert(
        [
            replace(
                event(chr(97 + i), title=f"Earthquake {i}"),
                published_at=NOW - timedelta(minutes=7 - i),
            )
            for i in range(7)
        ]
    )
    result = await retrieval(container).collect(user, AssistantQuestion("Recent earthquakes"))
    assert len(result.sources) == 6 and "a" not in {row.record_id for row in result.sources}


async def test_ambiguous_anaphoric_followup_asks_for_scope_without_reading_global_rows(
    container, user
):
    container.store.upsert((event(),))
    result = await retrieval(container).collect(
        user,
        AssistantQuestion(
            "Which of those are military?",
            prior_questions=("Flights in Ukraine",),
        ),
    )
    assert not result.sources and result.candidate_count == 0 and result.clarification
