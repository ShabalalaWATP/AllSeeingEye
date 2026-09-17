"""Restraint first: the live instruments are read only when the report actually asks.

The negative cases are the point of this file. A question that never mentions a
physical effect must not cause a single record to be counted, and a reading must
never report more inside the scope than the store actually held.
"""

from datetime import UTC, datetime, timedelta

import pytest

from ase.adapters.geo.area_geography import PackagedAreaGeography
from ase.application.ports.area_geography import ScopeRequest
from ase.application.reports.area_instruments import eligible_instruments, sweep_instruments
from ase.domain.area_assets import InstrumentClass
from ase.domain.area_instruments import (
    MAX_INSTRUMENT_READINGS,
    InstrumentReading,
    bound_readings,
    readings_from_list,
    readings_to_list,
)
from ase.domain.aviation import JamCell
from ase.domain.events import Category, Event, GeoConfidence, Point, Reliability
from test_asset_register_research import box

NOW = datetime(2026, 9, 17, 12, tzinfo=UTC)
KYIV_REGION = box(29.0, 49.5, 33.0, 51.5)
DRAWN = ScopeRequest(KYIV_REGION, ())


class Store:
    """Answers the one query the sweep makes and records that it was asked."""

    def __init__(self, events=()):
        self.events = list(events)
        self.queries = []

    def query(self, request):
        self.queries.append(request)
        categories = request.categories
        return [row for row in self.events if not categories or row.category in categories]


class Cells:
    def __init__(self, cells=()):
        self.rows = list(cells)

    def cells(self):
        return self.rows


def event(identity, category, lon, lat, *, tags=(), hours=1, title="A record"):
    return Event(
        id=identity,
        source_id="test",
        category=category,
        subtype="test",
        title=title,
        published_at=NOW - timedelta(hours=hours),
        observed_at=NOW,
        reliability=Reliability.F,
        point=Point(lon=lon, lat=lat),
        geo_confidence=GeoConfidence.EXACT,
        tags=frozenset(tags),
    )


def test_an_ordinary_question_makes_the_sweep_read_nothing_at_all():
    store = Store([event("E1", Category.AVIATION, 30.5, 50.4)])
    wanted = eligible_instruments(
        "Assess the coalition talks after the Dutch general election.", drawn=False
    )
    assert wanted == ()
    assert sweep_instruments(PackagedAreaGeography(), wanted, DRAWN, store, NOW) == ()
    assert store.queries == []


def test_only_the_named_instrument_is_read_even_where_others_hold_records():
    store = Store(
        [
            event("E1", Category.AVIATION, 30.5, 50.4),
            event("E2", Category.MARITIME, 30.6, 50.5),
        ]
    )
    wanted = eligible_instruments("Assess shadow fleet vessel movements.", drawn=False)
    assert wanted == (InstrumentClass.VESSEL_ACTIVITY,)
    readings = sweep_instruments(PackagedAreaGeography(), wanted, DRAWN, store, NOW)
    assert [row.instrument for row in readings] == ["vessel_activity"]
    assert [request.categories for request in store.queries] == [frozenset({Category.MARITIME})]


def test_a_drawn_area_is_itself_the_request_for_every_instrument():
    assert set(eligible_instruments("anything at all", drawn=True)) == set(InstrumentClass)


def test_records_outside_the_scope_are_counted_but_never_reported_as_inside():
    store = Store(
        [
            event("E1", Category.AVIATION, 30.5, 50.4, title="Inside Kyiv"),
            event("E2", Category.AVIATION, 2.35, 48.85, title="Over Paris"),
        ]
    )
    readings = sweep_instruments(
        PackagedAreaGeography(), (InstrumentClass.AIRCRAFT_ACTIVITY,), DRAWN, store, NOW
    )
    assert len(readings) == 1
    reading = readings[0]
    assert (reading.inside, reading.considered) == (1, 2)
    assert reading.examples == ("Inside Kyiv",)
    assert "not a claim about a mission" in reading.describe()


def test_a_thermal_sweep_reads_only_the_thermal_feed_inside_the_disaster_category():
    store = Store(
        [
            event("E1", Category.DISASTER, 30.5, 50.4, tags=("firms",), title="Thermal"),
            event("E2", Category.DISASTER, 30.6, 50.5, title="Flood warning"),
        ]
    )
    readings = sweep_instruments(
        PackagedAreaGeography(), (InstrumentClass.THERMAL_DETECTIONS,), DRAWN, store, NOW
    )
    assert (readings[0].inside, readings[0].considered) == (1, 1)
    assert "not a fire boundary" in readings[0].basis


def test_the_window_reported_is_the_window_the_store_actually_held():
    store = Store(
        [
            event("E1", Category.AVIATION, 30.5, 50.4, hours=1),
            event("E2", Category.AVIATION, 30.6, 50.5, hours=7),
        ]
    )
    readings = sweep_instruments(
        PackagedAreaGeography(), (InstrumentClass.AIRCRAFT_ACTIVITY,), DRAWN, store, NOW
    )
    assert readings[0].window_hours == 7


def test_an_instrument_holding_nothing_produces_no_reading_rather_than_a_zero():
    store = Store([event("E1", Category.AVIATION, 30.5, 50.4)])
    readings = sweep_instruments(
        PackagedAreaGeography(),
        (InstrumentClass.VESSEL_ACTIVITY, InstrumentClass.AIRCRAFT_ACTIVITY),
        DRAWN,
        store,
        NOW,
    )
    assert [row.instrument for row in readings] == ["aircraft_activity"]


def test_interference_cells_are_read_only_when_a_map_is_supplied():
    store = Store()
    degraded = JamCell(lon=30.5, lat=50.4, size=1.0, good=10, bad=9)
    far = JamCell(lon=2.5, lat=48.8, size=1.0, good=10, bad=9)
    quiet = JamCell(lon=31.5, lat=50.4, size=1.0, good=100, bad=1)
    wanted = (InstrumentClass.GNSS_INTERFERENCE,)
    assert sweep_instruments(PackagedAreaGeography(), wanted, DRAWN, store, NOW) == ()
    readings = sweep_instruments(
        PackagedAreaGeography(), wanted, DRAWN, store, NOW, Cells([degraded, far, quiet])
    )
    assert (readings[0].inside, readings[0].considered) == (1, 2)
    assert readings[0].window_hours == 24
    assert "never confirmation of" in readings[0].basis
    assert "low accuracy" in readings[0].examples[0]


def test_a_scope_that_does_not_resolve_places_nothing_inside_it():
    store = Store([event("E1", Category.AVIATION, 30.5, 50.4)])
    readings = sweep_instruments(
        PackagedAreaGeography(),
        (InstrumentClass.AIRCRAFT_ACTIVITY,),
        ScopeRequest(None, ()),
        store,
        NOW,
    )
    assert (readings[0].inside, readings[0].considered) == (0, 1)


def test_a_reading_survives_a_round_trip_and_refuses_impossible_counts():
    reading = InstrumentReading("aircraft_activity", "Aircraft", 1, 2, 6, "Basis.", ("One",))
    assert readings_from_list(readings_to_list((reading,))) == (reading,)
    with pytest.raises(ValueError):
        InstrumentReading("aircraft_activity", "Aircraft", 3, 2, 6, "Basis.")
    with pytest.raises(ValueError):
        InstrumentReading("aircraft_activity", "Aircraft", 1, 2, 0, "Basis.")
    with pytest.raises(ValueError):
        InstrumentReading("", "Aircraft", 1, 2, 6, "Basis.")
    with pytest.raises(ValueError):
        bound_readings(tuple(reading for _ in range(MAX_INSTRUMENT_READINGS + 1)))
    with pytest.raises(ValueError):
        readings_from_list([{"instrument": "x"}])
