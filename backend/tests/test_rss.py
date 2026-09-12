"""The generic feed connector reads RSS 2.0, RDF and Atom, and every seeded source is sound."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.rss import MAX_ITEMS, RssConnector, RssOptions, parse_feed_date, strip_html
from ase.adapters.feeds.rss_sources import RSS_SEEDS, US_ADVISORY, build_rss_connectors
from ase.domain.events import Category, Credibility, GeoConfidence, event_id
from ase.domain.sources import SourceKind
from feeds_helpers import FIXTURES, NOW, FakeClock, FakeHttp, make_spec


def read(name: str) -> str:
    return (FIXTURES / name).read_text("utf-8")


def connector(payload: str, options: RssOptions | None = None) -> RssConnector:
    http = FakeHttp({"feeds.test": payload})
    return RssConnector(http, FakeClock(NOW), make_spec("feed_test"), options)  # type: ignore[arg-type]


async def test_rss2_items_become_events() -> None:
    options = RssOptions(subtype="article", tags=frozenset({"x"}))
    events = await connector(read("rss2_sample.xml"), options).fetch()
    assert [event.title for event in events] == [
        "Mistrial declared in murder case, after jury deadlocks",
        "Escalating hostilities drive new displacement",
        "Undated item",
    ]
    first, second, third = events
    assert first.id == event_id("feed_test", "https://example.org/news/articles/cpwlrj2je1po#0")
    assert first.summary == "The mistrial puts the case & its future in limbo."
    assert first.url == "https://example.org/news/articles/cpwlrj2je1po?at_medium=RSS"
    assert first.published_at == datetime(2026, 9, 4, 22, 48, 38, tzinfo=UTC)
    assert first.attributes["author"] == "Sam Reporter"
    assert first.attributes["categories"] == "World, Courts"
    assert first.tags == frozenset({"x", "article"})
    assert first.geo_confidence is GeoConfidence.NONE and first.point is None
    assert first.category is Category.DISASTER  # from the spec, whatever the feed says
    assert first.credibility is Credibility.POSSIBLY_TRUE
    assert second.point is not None
    assert (second.point.lon, second.point.lat) == (34.2, 11.45)
    assert second.geo_confidence is GeoConfidence.EXACT
    assert (
        second.summary == "Country: Sudan More than 23,000 people have reportedly been displaced."
    )
    assert third.published_at is None
    assert third.id == event_id("feed_test", "https://example.org/undated")
    assert third.summary is None and third.attributes["author"] is None


async def test_rdf_and_atom_feeds() -> None:
    rdf = await connector(read("rdf_sample.xml")).fetch()
    assert len(rdf) == 2
    assert rdf[0].title == "Outrage as tycoon acquitted in journalist's murder"
    assert rdf[0].published_at is None
    assert rdf[0].source_dates[0].role == "unspecified"
    assert rdf[0].source_dates[0].value == datetime(2026, 9, 4, 19, 31, tzinfo=UTC)
    assert rdf[0].attributes["categories"] is None
    assert rdf[1].published_at is None and rdf[1].summary is None

    atom = await connector(read("atom_sample.xml")).fetch()
    assert len(atom) == 1
    entry = atom[0]
    assert entry.url == "https://example.gov/foreign-travel-advice/mauritius"
    assert entry.summary == (
        "Updated information on Ebola and travelling from Reunion Island (Entry requirements)"
    )
    assert entry.published_at is None
    assert entry.source_dates[0].role == "modification"
    assert entry.source_dates[0].value == datetime(2026, 9, 4, 15, 8, 37, tzinfo=UTC)
    assert entry.attributes["author"] == "FCDO"
    assert entry.attributes["categories"] == "travel"


async def test_country_codes_from_category_domains() -> None:
    events = await connector(read("rss_state_sample.xml"), US_ADVISORY).fetch()
    assert len(events) == 2
    assert events[0].country_iso == "BE"
    assert events[0].geo_confidence is GeoConfidence.COUNTRY
    assert events[0].subtype == "travel_advisory"
    assert events[0].published_at is None
    assert events[1].country_iso is None
    assert events[1].geo_confidence is GeoConfidence.NONE


async def test_malformed_feed_not_modified_bom_and_cap() -> None:
    with pytest.raises(FeedFetchError):
        await connector("<rss><channel><item>").fetch()
    unchanged = RssConnector(FakeHttp(not_modified=True), FakeClock(NOW), make_spec())  # type: ignore[arg-type]
    assert await unchanged.fetch() == []
    with_bom = "﻿" + read("rdf_sample.xml")
    assert len(await connector(with_bom).fetch()) == 2
    items = "".join(
        f"<item><title>t{i}</title><link>https://e.org/{i}</link></item>"
        for i in range(MAX_ITEMS + 50)
    )
    events = await connector(f"<rss><channel>{items}</channel></rss>").fetch()
    assert len(events) == MAX_ITEMS


def test_helpers() -> None:
    assert parse_feed_date("") is None
    assert parse_feed_date("garbage") is None
    assert parse_feed_date("2026-09-04T19:31:00Z") == datetime(2026, 9, 4, 19, 31, tzinfo=UTC)
    naive = parse_feed_date("2026-09-04 10:00:00")
    assert naive is None
    assert strip_html(None) is None
    assert strip_html("<p></p>") is None
    assert strip_html("a &lt;b&gt;c&lt;/b&gt;") == "a c"
    assert strip_html("plain &amp; simple") == "plain & simple"


def test_seeds_are_sound() -> None:
    ids = [seed.spec.id for seed in RSS_SEEDS]
    assert len(ids) == len(set(ids))
    for seed in RSS_SEEDS:
        spec = seed.spec
        assert spec.url.startswith("https://"), spec.id
        assert spec.kind is SourceKind.RSS
        assert spec.poll_interval.total_seconds() >= 15 * 60, spec.id
        assert spec.homepage.startswith("https://"), spec.id
        assert spec.licence_note, spec.id
        assert spec.category in (
            Category.NEWS,
            Category.POLITICAL,
            Category.HUMANITARIAN,
            Category.SOCIAL,
            Category.ECONOMIC,
            Category.CYBER,
        )
        if "state_controlled" in spec.flags:
            assert seed.options.credibility is Credibility.DOUBTFUL
            assert "state_controlled" in seed.options.tags
    connectors = build_rss_connectors(FakeHttp(), FakeClock(NOW))  # type: ignore[arg-type]
    assert [c.spec.id for c in connectors] == ids


def test_registry_includes_and_can_disable_feeds() -> None:
    every = build_connectors(FakeHttp(), FakeClock(NOW))  # type: ignore[arg-type]
    all_ids = {c.spec.id for c in every}
    assert {
        "usgs_earthquakes",
        "gdacs",
        "gdelt_events",
        "adsb_mil",
        "bbc_world",
        "tass_en",
    } <= all_ids
    fewer = build_connectors(FakeHttp(), FakeClock(NOW), disabled=["bbc_world", " tass_en "])  # type: ignore[arg-type]
    assert {"bbc_world", "tass_en"}.isdisjoint({c.spec.id for c in fewer})
    assert len(fewer) == len(every) - 2
