"""Map feature search: a fixed vocabulary, one bounded Overpass request, exact area checks."""

from dataclasses import replace

import httpx

from ase.adapters.research.osm_features import (
    ENDPOINT,
    MAX_FEATURES,
    SOURCE_ID,
    OsmFeaturesResearchProvider,
    area_km2,
    overpass_query,
)
from ase.domain.events import event_id
from ase.domain.osm_features import FEATURE_CLASSES, classes_for, feature_class
from ase.domain.research import CollectionStatus, ResearchFocus
from hazard_area_helpers import QUERY, area
from research_feed_helpers import CLOCK, PublicFeed

# About 490 square kilometres: well inside the map search bound.
SMALL = area([[[0, 0], [0.2, 0], [0.2, 0.2], [0, 0.2], [0, 0]]])
CHURCH_QUERY = replace(
    QUERY,
    area=SMALL,
    question="Which church or railway station near a bridge could this be?",
    terms=("church", "bridge"),
    focus=ResearchFocus.GENERAL,
)


def element(kind: str, ident: int, lat: float, lon: float, **tags: str) -> dict:
    position = {"lat": lat, "lon": lon} if kind == "node" else {"center": {"lat": lat, "lon": lon}}
    return {"type": kind, "id": ident, "tags": tags, **position}


def test_vocabulary_is_bounded_and_matches_plain_words() -> None:
    keys = [feature.key for feature in classes_for("a church beside the railway station")]
    assert keys == ["church", "railway_station"]
    assert classes_for("Churches near bridges")[0].key == "church"
    # Plural and hyphenated forms count; substrings inside other words do not.
    assert not classes_for("archbishop's damson orchard")
    assert len(classes_for(" ".join(f.words[0] for f in FEATURE_CLASSES))) == 6
    assert feature_class("stadium") is not None and feature_class("spaceport") is None
    assert len({feature.key for feature in FEATURE_CLASSES}) == len(FEATURE_CLASSES)


def test_overpass_query_names_only_the_requested_kinds_inside_the_box() -> None:
    query = overpass_query(classes_for("church and bridge"), (0.0, 0.0, 10.0, 10.0))
    assert query.startswith("[out:json][timeout:25][bbox:0.000000,0.000000,10.000000,10.000000];")
    assert '["amenity"="place_of_worship"]["religion"="christian"]' in query
    assert '["man_made"="bridge"]' in query and "hospital" not in query
    assert query.endswith(f"out center tags {MAX_FEATURES};")
    assert area_km2((0.0, 0.0, 1.0, 1.0)) < 12_400 < area_km2((0.0, 0.0, 1.0, 1.1))


def provider(monkeypatch, elements):
    feed = PublicFeed(monkeypatch, httpx.Response(200, json={"elements": elements}))
    return OsmFeaturesResearchProvider(feed.http, CLOCK), feed


async def test_one_guarded_request_and_only_features_inside_the_polygon(monkeypatch) -> None:
    service, feed = provider(
        monkeypatch,
        [
            element(
                "node",
                1,
                0.1,
                0.1,
                name="St Mary",
                amenity="place_of_worship",
                religion="christian",
            ),
            element("way", 2, 0.15, 0.15, **{"name:en": "Old Bridge", "man_made": "bridge"}),
            element("node", 3, 40.0, 40.0, amenity="place_of_worship", religion="christian"),
            element("node", 4, 0.12, 0.12, amenity="hospital"),
            {"type": "node", "id": 5, "lat": 0.11, "lon": 0.11},
        ],
    )
    result = await service.collect(CHURCH_QUERY)
    assert len(feed.requests) == len(feed.guarded) == 1
    assert feed.requests[0].url.host == "overpass-api.de"
    assert str(feed.requests[0].url).startswith(ENDPOINT)
    assert [item.title for item in result.items] == ["Church: St Mary", "Bridge: Old Bridge"]
    church = result.items[0]
    assert church.id == event_id(SOURCE_ID, "node/1") and church.source_id == SOURCE_ID
    assert church.url == "https://www.openstreetmap.org/node/1"
    assert church.published_at is None and church.observed_at == CLOCK.now()
    assert church.geometry is not None
    assert church.geometry.to_geometry() == {"type": "Point", "coordinates": [0.1, 0.1]}
    assert church.attributes["feature_class"] == "church"
    assert "religion=christian" in str(church.attributes["tags"])
    attempt = result.attempts[0]
    assert attempt.status is CollectionStatus.COMPLETED and attempt.source_id == SOURCE_ID
    assert "Looked for: church, railway station, bridge." in attempt.explanation
    assert "3 features excluded" in attempt.explanation
    await feed.http.aclose()


async def test_unsupported_without_an_area_or_a_named_kind(monkeypatch) -> None:
    service, feed = provider(monkeypatch, [])
    no_area = await service.collect(replace(CHURCH_QUERY, area=None))
    no_kind = await service.collect(replace(CHURCH_QUERY, question="What happened here?", terms=()))
    assert no_area.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert no_kind.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not feed.requests
    empty = await service.collect(CHURCH_QUERY)
    assert empty.attempts[0].status is CollectionStatus.EMPTY and not empty.items
    await feed.http.aclose()


async def test_a_busy_overpass_server_is_reported_as_unavailable(monkeypatch) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(504, text="Gateway timeout"))
    result = await OsmFeaturesResearchProvider(feed.http, CLOCK).collect(CHURCH_QUERY)
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert "busy" in result.attempts[0].explanation
    await feed.http.aclose()


async def test_failures_and_oversized_answers_become_safe_receipts(monkeypatch) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(500, text="secret area leak"))
    failed = await OsmFeaturesResearchProvider(feed.http, CLOCK).collect(CHURCH_QUERY)
    assert failed.attempts[0].status is CollectionStatus.FAILED
    assert "leak" not in failed.attempts[0].explanation
    await feed.http.aclose()
    too_many = [
        element("node", n, 0.1, 0.1, amenity="place_of_worship", religion="christian")
        for n in range(MAX_FEATURES + 1)
    ]
    service, feed = provider(monkeypatch, too_many)
    result = await service.collect(CHURCH_QUERY)
    assert result.attempts[0].status is CollectionStatus.FAILED
    await feed.http.aclose()
