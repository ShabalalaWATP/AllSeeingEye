"""General news has its own bounded geography feed, not fabricated RSS locations."""

import pytest

from ase.adapters.feeds.gdelt_events import ROOT_CODES, GdeltEventsConnector
from ase.adapters.feeds.gdelt_news import NEWS_ROOTS, GdeltNewsConnector
from ase.adapters.feeds.registry import build_connectors
from ase.domain.events import Category, GeoConfidence
from ase.domain.evidence_time import EvidenceTimeBasis, MapTimeBasis, evidence_time
from feeds_helpers import NOW, FakeClock, FakeHttp
from test_gdelt_events import http_for, row


async def test_news_and_conflict_roots_are_disjoint_and_registered_separately() -> None:
    assert not NEWS_ROOTS.keys() & ROOT_CODES.keys()
    rows = [row(str(index), root=root) for index, root in enumerate([*NEWS_ROOTS, *ROOT_CODES])]
    news = await GdeltNewsConnector(http_for(rows), FakeClock(NOW)).fetch()
    conflicts = await GdeltEventsConnector(http_for(rows), FakeClock(NOW)).fetch()
    assert len(news) == 14 and len(conflicts) == 6
    assert {event.category for event in news} == {Category.NEWS}
    assert {event.category for event in conflicts} == {Category.CONFLICT}
    ids = {connector.spec.id for connector in build_connectors(FakeHttp(), FakeClock(NOW))}
    assert {"gdelt_news", "gdelt_events"} <= ids
    assert "gdelt_news" not in {
        connector.spec.id
        for connector in build_connectors(FakeHttp(), FakeClock(NOW), disabled=["gdelt_news"])
    }


@pytest.mark.parametrize(
    "geo_type,precision", [("1", GeoConfidence.COUNTRY), ("3", GeoConfidence.CITY)]
)
async def test_news_preserves_geography_uncertainty_indexing_time_and_original_article(
    geo_type, precision
) -> None:
    event = (
        await GdeltNewsConnector(
            http_for([row(root="04", geo_type=geo_type)]), FakeClock(NOW)
        ).fetch()
    )[0]
    assert event.source_id == "gdelt_news" and event.grade == "F6"
    assert event.geo_confidence is precision and event.point is not None
    assert event.country_iso is None  # GDELT FIPS 'UP' must never be used as ISO2.
    assert event.published_at is None
    assert evidence_time(event) is None
    assert evidence_time(event, EvidenceTimeBasis.RESEARCH) is None
    assert evidence_time(event, MapTimeBasis.MAP) == event.source_dates[0].value
    assert event.url == "https://example.org/report"
    assert "publisher publication time unknown" in event.attributes["date_basis"]
    assert "location unverified" in event.attributes["geography_basis"]
    assert event.severity is None and event.title.startswith("News signal:")
    assert "not the publisher headline" in event.attributes["content_scope"]


async def test_bad_locations_links_and_dates_do_not_become_current_mapped_news() -> None:
    undated = row("undated", root="01")
    undated[59] = "invalid"
    events = await GdeltNewsConnector(
        http_for(
            [
                undated,
                row("invalid-position", root="01", lat="91"),
                row("invalid-link", root="01", url="javascript:alert(1)"),
            ]
        ),
        FakeClock(NOW),
    ).fetch()
    assert len(events) == 1 and events[0].published_at is None


async def test_news_export_limit_and_repeated_batch_are_bounded() -> None:
    connector = GdeltNewsConnector(
        http_for([row(str(index), root="04") for index in range(450)]), FakeClock(NOW)
    )
    assert len(await connector.fetch()) == 400
    assert len(await connector.fetch()) == 400  # A connection test cannot consume a live batch.


@pytest.mark.parametrize("column,bad", [(31, "NaN"), (32, "Infinity"), (33, "1e309")])
async def test_malformed_counts_do_not_discard_valid_news(column, bad) -> None:
    malformed = row("bad", root="04")
    malformed[column] = bad
    connector = GdeltNewsConnector(http_for([malformed, row("good", root="01")]), FakeClock(NOW))
    events = await connector.fetch()
    assert len(events) == 2
