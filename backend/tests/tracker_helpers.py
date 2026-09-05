"""Events and a conflict shared by the tracker and tracker-report tests."""

from __future__ import annotations

from datetime import datetime, timedelta

from ase.domain.events import BoundingBox, Category, Event, Point
from ase.domain.trackers import Conflict
from feeds_helpers import NOW, make_event

UKRAINE = Conflict(
    id="ukraine",
    name="Russia's war in Ukraine",
    status="war",
    countries=("UA",),
    bbox=BoundingBox(west=22.0, south=44.0, east=41.0, north=52.5),
    keywords=("Kharkiv",),
)


def conflict_events(now: datetime = NOW) -> list[Event]:
    """Three conflict events in Ukraine across a fortnight, a news item there, one in Sudan."""
    return [
        make_event(
            "k1",
            source_id="gdelt",
            category=Category.CONFLICT,
            subtype="battle",
            title="Shelling in Kharkiv",
            point=Point(36.2, 49.9),
            country_iso="UA",
            severity=0.7,
            published_at=now,
        ),
        make_event(
            "k2",
            source_id="gdelt",
            category=Category.CONFLICT,
            subtype="strike",
            title="Drone strike near Sumy",
            point=Point(34.8, 50.9),
            country_iso="UA",
            published_at=now - timedelta(days=3),
            severity=0.9,
        ).with_changes(attributes={"fatalities": 4}),
        make_event(
            "k3",
            source_id="gdelt",
            category=Category.CONFLICT,
            subtype="battle",
            title="Last week's clash",
            point=Point(37.0, 48.5),
            country_iso="UA",
            published_at=now - timedelta(days=10),
        ),
        make_event(
            "n1",
            source_id="bbc",
            category=Category.NEWS,
            title="Talks in Kyiv",
            point=None,
            country_iso="UA",
            published_at=now,
        ),
        make_event(
            "far",
            source_id="gdelt",
            category=Category.CONFLICT,
            title="Clash in Sudan",
            point=Point(32.5, 15.6),
            country_iso="SD",
            published_at=now,
        ),
    ]


def disaster_events(now: datetime = NOW) -> list[Event]:
    """Two earthquakes (one last week), a cyclone, a red-tagged volcano and a landslide."""
    return [
        make_event(
            "q1",
            subtype="earthquake",
            title="M6.1 quake",
            severity=0.9,
            country_iso="JP",
            published_at=now,
        ),
        make_event(
            "q2",
            subtype="earthquake",
            title="M4.5 quake",
            severity=0.3,
            country_iso="JP",
            published_at=now - timedelta(days=9),
        ),
        make_event(
            "c1",
            subtype="tropical_cyclone",
            title="Hurricane Marie",
            severity=0.6,
            published_at=now,
        ),
        make_event(
            "v1", subtype="volcanoes", title="Ambae erupts", country_iso="VU", published_at=now
        ).with_changes(tags=frozenset({"volcanoes", "gdacs_red"})),
        make_event("x1", subtype="landslides", title="Landslide", published_at=now),
    ]
