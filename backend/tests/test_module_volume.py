"""Module boards retain their context when high-volume feeds fill the live store."""

from dataclasses import replace
from datetime import datetime, timedelta

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.feeds import EventQuery
from ase.application.trackers.modules import ModuleService
from ase.container import Container
from ase.domain.events import Category, Event
from feeds_helpers import NOW, make_event
from helpers import FakeClock
from test_modules import module_events


def newer_events(category: Category, subtype: str, source: str, now: datetime = NOW) -> list[Event]:
    return [
        make_event(
            f"newer-{index}",
            category=category,
            subtype=subtype,
            source_id=source,
            published_at=now,
            observed_at=now,
        )
        for index in range(5_001)
    ]


def test_ais_positions_do_not_hide_retained_navarea_warnings() -> None:
    store = InMemoryEventStore()
    context = module_events()
    store.upsert([*context, *newer_events(Category.MARITIME, "vessel_position", "aisstream")])

    board = ModuleService(store, FakeClock(NOW)).maritime_board()

    assert board.warnings_total == 2
    assert board.located == 1
    assert [event.id for event in board.latest] == [context[0].id, context[1].id]
    assert board.notable == (context[0],)
    assert [(row.key, row.count) for row in board.by_area] == [("4", 1), ("P", 1)]


def test_active_satellites_do_not_hide_launch_kp_and_noaa_context() -> None:
    store = InMemoryEventStore()
    context = [
        replace(event, published_at=NOW - timedelta(hours=3))
        for event in module_events()
        if event.category is Category.SPACE
    ]
    store.upsert([*context, *newer_events(Category.SPACE, "satellite", "celestrak_active")])

    board = ModuleService(store, FakeClock(NOW)).space_board()

    assert [event.title for event in board.launches] == ["Launch: Spectrum"]
    assert board.kp == 5.33
    assert board.kp_level == "storm"
    assert board.alerts_24h == 1
    assert [event.title for event in board.latest_alerts] == ["Geomagnetic storm watch"]
    assert [event.title for event in board.stations] == ["ISS (ZARYA)"]


def test_crewed_station_list_excludes_other_satellite_catalogues() -> None:
    store = InMemoryEventStore()
    station = module_events()[2]
    satellite = make_event(
        "active-satellite",
        source_id="celestrak_active",
        category=Category.SPACE,
        subtype="satellite",
        title="Non-crewed satellite",
    )
    store.upsert([station, satellite])

    assert ModuleService(store, FakeClock(NOW)).space_board().stations == (station,)


def test_other_cyber_subtypes_do_not_hide_outages_claims_and_kev() -> None:
    store = InMemoryEventStore()
    context = module_events()
    store.upsert([*context, *newer_events(Category.CYBER, "security_news", "cyber_rss")])

    board = ModuleService(store, FakeClock(NOW)).cyber_board()

    assert board.outages_24h == 1
    assert board.ransomware_7d == 1
    assert board.kev_7d == 1
    assert board.latest_outages == (context[7],)
    assert board.latest_claims == (context[8],)
    assert board.latest_kev == (context[9],)
    assert [(row.key, row.count) for row in board.ransomware_by_group] == [("akira", 1)]


async def test_maritime_report_background_retains_warnings_after_ais_saturation(
    container: Container,
) -> None:
    now = container.clock.now()
    container.store.upsert(
        [*module_events(now), *newer_events(Category.MARITIME, "vessel_position", "aisstream", now)]
    )

    background = await container._maritime_background()

    assert "Active broadcast warnings in the last fortnight: 2 (1 with positions)" in background
    assert "NAVAREA 4 1" in background
    assert "NAVAREA P 1" in background


def test_maritime_bounds_warning_counts_and_orders_samples_within_window() -> None:
    store = InMemoryEventStore()
    base = module_events()[0]
    warnings = [
        replace(base, id=f"warning-{index}", published_at=NOW - timedelta(seconds=index))
        for index in range(5_007)
    ]
    expired = replace(base, id="expired-warning", published_at=NOW - timedelta(days=15))
    store.upsert([expired, *reversed(warnings)])

    board = ModuleService(store, FakeClock(NOW)).maritime_board()

    assert board.warnings_total == 5_000
    assert board.located == 5_000
    assert [(row.key, row.count) for row in board.by_area] == [("4", 5_000)]
    assert board.latest == tuple(warnings[:50])
    assert board.notable == tuple(warnings[:20])


def test_cyber_bounds_outage_counts_and_orders_samples_within_window() -> None:
    store = InMemoryEventStore()
    context = module_events()
    outages = [
        replace(context[7], id=f"outage-{index}", published_at=NOW - timedelta(seconds=index))
        for index in range(5_007)
    ]
    expired_outage = replace(context[7], id="expired-outage", published_at=NOW - timedelta(days=2))
    expired_claim = replace(context[8], id="expired-claim", published_at=NOW - timedelta(days=8))
    expired_kev = replace(context[9], id="expired-kev", published_at=NOW - timedelta(days=8))
    store.upsert([expired_outage, expired_claim, expired_kev, *reversed(outages)])

    board = ModuleService(store, FakeClock(NOW)).cyber_board()

    assert board.outages_24h == 5_000
    assert [(row.key, row.count) for row in board.outages_by_country] == [("TN", 5_000)]
    assert board.latest_outages == tuple(outages[:30])
    assert board.ransomware_7d == 0
    assert board.kev_7d == 0


def test_subtype_filter_applies_before_the_query_limit() -> None:
    store = InMemoryEventStore()
    context = module_events()
    store.upsert([*context, *newer_events(Category.MARITIME, "vessel_position", "aisstream")])

    warnings = store.query(
        EventQuery(
            categories=frozenset({Category.MARITIME}),
            subtypes=frozenset({"navarea_warning"}),
            limit=1,
        )
    )

    assert warnings == [context[0]]
