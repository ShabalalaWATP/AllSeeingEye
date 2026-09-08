"""Provisional credibility, related topics, declared provenance and bounded windows."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.grading import GradingService, profiles_from_specs
from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.ports.feeds import BusMessage
from ase.domain.events import Category, Credibility, Point
from ase.domain.grading import (
    build_stories,
    distance_km,
    grade_events,
    jaccard,
    title_tokens,
)
from feeds_helpers import NOW, FakeClock, FakeConnector, make_event, make_spec
from grading_helpers import PROFILES, news


def test_tokens_similarity_and_distance() -> None:
    event = news("t", "bbc", "RSF forces enter El Fasher after weeks of siege, says the UN")
    assert title_tokens(event) == frozenset({"rsf", "force", "enter", "fasher", "week", "siege"})
    assert jaccard(frozenset({"a", "b"}), frozenset({"b", "c"})) == 1 / 3
    assert jaccard(frozenset(), frozenset({"x"})) == 0.0
    london, paris = Point(lon=-0.1276, lat=51.5072), Point(lon=2.3522, lat=48.8566)
    assert 340 < distance_km(london, paris) < 345


def test_related_reporting_across_outlets_is_not_verified_corroboration() -> None:
    first = news("a", "bbc", "RSF forces enter El Fasher after weeks of siege", minutes=0)
    second = news("b", "aljazeera", "Sudan: RSF fighters enter El Fasher as siege ends", minutes=38)
    third = news("c", "reuters_via_guardian", "RSF enters El Fasher, ending the siege", minutes=95)
    unrelated = news("d", "bbc", "Cabinet reshuffle in Khartoum announced", minutes=10)
    graded = {g.event.id: g for g in grade_events([first, second, third, unrelated], PROFILES)}
    assert graded[first.id].credibility is Credibility.CANNOT_BE_JUDGED
    assert "3 declared organisation group(s)" in graded[first.id].rationale
    assert "independent sourcing and claim agreement not verified" in graded[first.id].rationale
    assert graded[first.id].story_id == graded[second.id].story_id == graded[third.id].story_id
    assert graded[unrelated.id].story_id != graded[first.id].story_id
    # The unrelated item has context (same country, same category) but no corroboration.
    assert graded[unrelated.id].credibility is Credibility.CANNOT_BE_JUDGED
    assert "Area/category context (3 other item(s))" in graded[unrelated.id].rationale


def test_related_outlet_reporting_and_possible_copies() -> None:
    first = news("a", "bbc", "Heavy fighting reported around Kharkiv overnight", minutes=0)
    copy = news("b", "bbc_arabic", "Heavy fighting reported around Kharkiv overnight", minutes=5)
    other = news(
        "c", "aljazeera", "Overnight fighting reported near Kharkiv, officials say", minutes=50
    )
    graded = {g.event.id: g for g in grade_events([first, copy, other], PROFILES)}
    assert graded[first.id].credibility is Credibility.CANNOT_BE_JUDGED
    assert "2 declared organisation group(s)" in graded[first.id].rationale
    assert "claim agreement not verified" in graded[other.id].rationale
    syndicated = news(
        "d", "reuters_via_guardian", "Heavy fighting reported around Kharkiv overnight", minutes=8
    )
    graded = {g.event.id: g for g in grade_events([first, syndicated], PROFILES)}
    # A near-identical title could be a copy; it cannot establish independent agreement.
    assert graded[first.id].credibility is Credibility.CANNOT_BE_JUDGED
    assert "1 declared organisation group(s)" in graded[first.id].rationale
    assert graded[first.id].rationale.endswith(
        "; near-identical headlines or content may be copies, grouped once"
    )


def test_single_source_rules() -> None:
    lone = news("a", "bbc", "Minister resigns over procurement scandal", country=None)
    state = news("b", "tass", "Ministry reports successful missile test", country="RU")
    quake = make_event(
        "q", source_id="usgs", title="M5.1 - 20 km E of Tokyo", point=Point(139.9, 35.7)
    )
    kev = make_event(
        "k",
        source_id="kev",
        category=Category.CYBER,
        subtype="kev",
        title="CVE-2026-1 added",
        point=None,
    )
    graded = {g.event.id: g for g in grade_events([lone], PROFILES)}
    assert graded[lone.id].credibility is Credibility.CANNOT_BE_JUDGED
    graded = {g.event.id: g for g in grade_events([state], PROFILES)}
    assert graded[state.id].credibility is Credibility.POSSIBLY_TRUE
    assert "State-controlled" in graded[state.id].rationale
    graded = {g.event.id: g for g in grade_events([quake, kev], PROFILES)}
    assert graded[quake.id].credibility is Credibility.PROBABLY_TRUE
    assert graded[kev.id].credibility is Credibility.PROBABLY_TRUE
    unknown = make_event("u", source_id="mystery", category=Category.NEWS, point=None)
    graded = {g.event.id: g for g in grade_events([unknown], PROFILES)}
    assert graded[unknown.id].credibility is Credibility.CANNOT_BE_JUDGED


def test_disasters_link_by_place_and_time_and_windows_apply() -> None:
    usgs = make_event(
        "q1",
        source_id="usgs",
        subtype="earthquake",
        title="M6.0 - 30 km S of Kalamata",
        point=Point(22.1, 36.8),
    )
    gdacs = make_event(
        "q2", source_id="gdacs", subtype="earthquake", title="Orange alert, earthquake: Greece",
        point=Point(22.3, 36.6), published_at=NOW + timedelta(hours=1),
    )  # fmt: skip
    far = make_event(
        "q3",
        source_id="gdacs",
        subtype="earthquake",
        title="Green alert, earthquake: Peru",
        point=Point(-76.0, -12.0),
    )
    late = make_event(
        "q4",
        source_id="gdacs",
        subtype="earthquake",
        title="Orange alert, earthquake: Greece",
        point=Point(22.2, 36.7),
        published_at=NOW + timedelta(days=3),
    )
    stories = build_stories([usgs, gdacs, far, late])
    assert sorted(sorted(e.id for e in story) for story in stories) == sorted(
        [sorted([usgs.id, gdacs.id]), [far.id], [late.id]]
    )
    graded = {g.event.id: g for g in grade_events([usgs, gdacs, far], PROFILES)}
    assert graded[usgs.id].credibility is Credibility.PROBABLY_TRUE
    assert "Provisional instrument" in graded[usgs.id].rationale
    assert "not independently verified" in graded[usgs.id].rationale
    assert graded[usgs.id].story_id != graded[gdacs.id].story_id
    old = news("x", "bbc", "Flooding closes the coast road near Kalamata", minutes=-60 * 72)
    new = news("y", "aljazeera", "Flooding closes the coast road near Kalamata", minutes=0)
    assert len(build_stories([old, new])) == 2


async def test_service_and_scheduler_regrade_neighbours() -> None:
    specs = [make_spec("bbc"), replace(make_spec("aljazeera"), organisation="Al Jazeera")]
    profiles = profiles_from_specs(specs)
    assert profiles["bbc"].independence_key == "Test Org"
    store = InMemoryEventStore()
    clock = FakeClock(NOW)
    first = news("a", "bbc", "Heavy fighting reported around Kharkiv overnight")
    store.upsert([first])
    service = GradingService(store, profiles, clock)
    assert [e.id for e in service.regrade([first])] == [first.id]
    assert store.get(first.id) is not None
    assert store.get(first.id).credibility is Credibility.CANNOT_BE_JUDGED  # type: ignore[union-attr]
    assert service.regrade([first]) == []  # nothing moved the second time

    class Bus:
        def __init__(self) -> None:
            self.messages: list[BusMessage] = []

        async def publish(self, message: BusMessage) -> None:
            self.messages.append(message)

        def subscribe(self) -> object:
            raise NotImplementedError

    bus = Bus()
    second = news(
        "b", "aljazeera", "Overnight fighting reported near Kharkiv, officials say", minutes=40
    )
    connector = FakeConnector(specs[1], [second])
    scheduler = FeedScheduler(
        [connector],
        Pipeline([Normaliser()]),
        store,
        bus,
        HealthRegistry(),
        clock,
        grader=service,  # type: ignore[arg-type]
    )
    outcome = await scheduler.poll_once(connector)
    assert outcome.ok and outcome.changed == 1
    upsert = next(m for m in bus.messages if m.kind == "event.upsert")
    published = {e.id: e for e in upsert.payload["events"]}  # type: ignore[union-attr]
    # Both the new item and its regraded neighbour go out, with their stored grades.
    assert set(published) == {first.id, second.id}
    assert published[first.id].credibility is Credibility.CANNOT_BE_JUDGED
    assert published[second.id].credibility is Credibility.CANNOT_BE_JUDGED
    assert published[first.id].story_id == published[second.id].story_id
