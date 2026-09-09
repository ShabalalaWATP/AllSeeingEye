"""Worldwide page diversity without changing scope, time filters or newest defaults."""

from dataclasses import replace
from datetime import timedelta

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.feeds import EventQuery
from ase.domain.events import BoundingBox, Category, Point
from feeds_helpers import NOW, make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


def worldwide_events():
    cluster = [make_event(f"cluster-{index}") for index in range(100)]
    worldwide = [
        make_event(f"world-{index}", point=point, published_at=NOW - timedelta(hours=1))
        for index, point in enumerate((Point(-100, 40), Point(140, 35), Point(25, -30)))
    ]
    return cluster, worldwide


def test_geographic_selection_precedes_limit_and_default_stays_newest():
    store = InMemoryEventStore()
    cluster, worldwide = worldwide_events()
    store.upsert(cluster + worldwide)
    newest = store.query(EventQuery(limit=4))
    sampled = store.query(EventQuery(limit=4, sampling="geographic"))
    assert {event.id for event in newest} <= {event.id for event in cluster}
    assert {event.id for event in worldwide} <= {event.id for event in sampled}
    assert len(sampled) == 4
    assert newest == store.query(EventQuery(limit=4, sampling="newest"))


def test_pages_are_complete_disjoint_and_independent_of_insertion_order():
    cluster, worldwide = worldwide_events()
    unlocated = [make_event(f"unknown-{index}", point=None) for index in range(8)]
    events = cluster + worldwide + unlocated
    stores = [InMemoryEventStore(), InMemoryEventStore()]
    stores[0].upsert(events)
    stores[1].upsert(reversed(events))
    query = EventQuery(limit=200, sampling="geographic")
    full = stores[0].query(query)
    pages = [
        event
        for offset in range(0, len(events), 7)
        for event in stores[0].query(replace(query, offset=offset, limit=7))
    ]
    assert pages == full == stores[1].query(query)
    assert len({event.id for event in pages}) == len(events)
    assert all(event.point is not None for event in full[:4])
    assert full[4].point is None
    assert stores[0].query(replace(query, offset=len(events))) == []


def test_all_filters_precede_geographic_cells_and_dateline_is_honoured():
    store = InMemoryEventStore()
    base = make_event("east", point=Point(179, 2), country_iso="FJ", source_id="selected")
    west = replace(base, id="west", point=Point(-179, 2))
    rejected = [
        replace(base, id="old", published_at=NOW - timedelta(days=3)),
        replace(base, id="future", published_at=NOW + timedelta(days=3)),
        replace(base, id="country", country_iso="DE"),
        replace(base, id="source", source_id="other"),
        replace(base, id="category", category=Category.CYBER),
        replace(base, id="outside", point=Point(0, 2)),
        replace(base, id="unlocated", point=None),
    ]
    store.upsert([base, west, *rejected])
    query = EventQuery(
        sampling="geographic",
        categories=frozenset({Category.DISASTER}),
        country_iso="FJ",
        source_ids=frozenset({"selected"}),
        bbox=BoundingBox(170, -10, -170, 10),
        since=NOW - timedelta(days=1),
        until=NOW + timedelta(days=1),
        limit=1,
    )
    assert {store.query(query)[0].id, store.query(replace(query, offset=1))[0].id} == {
        base.id,
        west.id,
    }
    assert store.query(replace(query, offset=2)) == []


def test_unlocated_only_and_exact_poles_remain_valid():
    store = InMemoryEventStore()
    unknown = [make_event(f"unknown-{index}", point=None) for index in range(3)]
    store.upsert(unknown)
    assert store.query(EventQuery(sampling="geographic")) == store.query(EventQuery())
    poles = [make_event("north", point=Point(180, 90)), make_event("south", point=Point(-180, -90))]
    store.upsert(poles)
    assert {e.id for e in store.query(EventQuery(sampling="geographic", limit=2))} == {
        e.id for e in poles
    }


def test_military_filter_is_not_displaced_by_civilian_cells():
    store = InMemoryEventStore()
    military = make_event("military", category=Category.AVIATION, subtype="military_aircraft")
    civil = make_event("civil", category=Category.AVIATION, point=Point(-100, 40))
    store.upsert([military, civil])
    assert store.query(EventQuery(sampling="geographic", military=True, limit=1)) == [military]
    assert store.query(EventQuery(sampling="geographic", military=False, limit=1)) == [civil]


def test_categories_rotate_inside_cells_without_giving_multicategory_cells_extra_turns():
    store = InMemoryEventStore()
    fires = [make_event(f"fire-{index}") for index in range(20)]
    flight = make_event("flight", category=Category.AVIATION, published_at=NOW - timedelta(hours=1))
    ship = make_event("ship", category=Category.MARITIME, published_at=NOW - timedelta(hours=2))
    distant = [make_event(f"distant-{index}", point=Point(-100, 40)) for index in range(4)]
    store.upsert([*fires, flight, ship, *distant])
    query = EventQuery(sampling="geographic", limit=6)
    page = store.query(query)
    local = [event for event in page if event.point == flight.point]
    assert [event.category for event in local] == [
        Category.DISASTER,
        Category.AVIATION,
        Category.MARITIME,
    ]
    assert len([event for event in page if event.point == distant[0].point]) == 3
    assert page == store.query(replace(query, limit=3)) + store.query(
        replace(query, offset=3, limit=3)
    )


async def test_sampling_api_validation_authentication_and_real_selection(client, container, user):
    cluster, worldwide = worldwide_events()
    container.store.upsert(cluster + worldwide)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    response = await client.get(
        "/api/events", params={"sampling": "geographic", "limit": 4}, headers=headers
    )
    assert response.status_code == 200
    assert {e.id for e in worldwide} <= {row["id"] for row in response.json()["items"]}
    for params in (
        {"sampling": "random"},
        {"sampling": "geographic", "limit": 2001},
        {"sampling": "geographic", "offset": 15001},
    ):
        assert (await client.get("/api/events", params=params, headers=headers)).status_code == 422
    assert (await client.get("/api/events", params={"sampling": "geographic"})).status_code == 401
