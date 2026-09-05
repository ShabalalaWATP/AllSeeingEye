"""The aviation tracker: interference map, baselines, the board API and the report background."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta

from httpx import AsyncClient

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.trackers.aviation import (
    AviationMonitor,
    WatchedArea,
    samples_for,
    summary_text,
)
from ase.container import Container
from ase.domain.aviation import JamMap, is_bad, military_by_country
from ase.domain.events import Category, Event, Point
from ase.domain.users import User
from feeds_helpers import NOW, make_event
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    bearer,
    login_token,
)
from report_helpers import PROFILE, ScriptedGateway, good_body


def aircraft(
    key: str,
    *,
    lon: float,
    lat: float,
    nac_p: float | None,
    tags: set[str] | None = None,
    country: str | None = "UA",
    severity: float | None = None,
    now: datetime = NOW,
) -> Event:
    event = make_event(
        key,
        source_id="adsb_mil",
        category=Category.AVIATION,
        subtype="military_aircraft",
        title=f"Aircraft {key}",
        point=Point(lon, lat),
        country_iso=country,
        published_at=now,
        observed_at=now,
        severity=severity,
    )
    attributes = {"icao_hex": key, "track_deg": 90}
    if nac_p is not None:
        attributes["nac_p"] = nac_p
    return event.with_changes(tags=frozenset(tags or {"military", "adsb"}), attributes=attributes)


def fleet(now: datetime = NOW) -> list[Event]:
    """Six aircraft in one cell over Ukraine (two with poor accuracy), plus extras."""
    events = [aircraft(f"g{i}", lon=36.2 + i * 0.05, lat=49.9, nac_p=9, now=now) for i in range(4)]
    events += [aircraft(f"b{i}", lon=36.4, lat=49.7 + i * 0.05, nac_p=3, now=now) for i in range(2)]
    events.append(
        aircraft(
            "area1",
            lon=33.5,
            lat=45.0,
            nac_p=None,
            tags={"adsb", "area_watch", "area_black_sea"},
            now=now,
        )
    )
    events.append(
        aircraft(
            "sos",
            lon=30.0,
            lat=50.0,
            nac_p=10,
            tags={"adsb", "emergency", "squawk_7700"},
            country="PL",
            severity=0.8,
            now=now,
        )
    )
    return events


def test_jam_map_counts_bad_aircraft_per_cell_over_a_rolling_day() -> None:
    jam = JamMap()
    assert jam.observe(fleet(), NOW) == 7  # the area aircraft has no accuracy field
    cells = jam.cells()
    assert len(cells) == 1
    cell = cells[0]
    assert (cell.good, cell.bad) == (4, 2) and cell.percent_bad == 16.7 and cell.level == "red"
    assert (cell.lon, cell.lat, cell.size) == (36.5, 49.5, 1.0)
    # The same airframes an hour later count once more; a day later the first hour is gone.
    jam.observe(fleet(NOW + timedelta(hours=1)), NOW + timedelta(hours=1))
    assert jam.cells()[0].good == 8
    jam.observe([], NOW + timedelta(hours=26))
    assert jam.cells() == [] and jam.updated_at == NOW + timedelta(hours=26)
    assert is_bad(aircraft("x", lon=0, lat=0, nac_p=None)) is None
    assert military_by_country(fleet()) == {"UA": 6}  # the emergency and area aircraft are civil


class RecordingSink:
    def __init__(self) -> None:
        self.rows: list[tuple[datetime, tuple[str, str, int]]] = []

    async def record_many(self, hour: datetime, samples: list[tuple[str, str, int]]) -> None:
        self.rows.extend((hour, sample) for sample in samples)


async def test_monitor_samples_and_can_run_in_the_background() -> None:
    store = InMemoryEventStore()
    store.upsert(fleet())
    sink = RecordingSink()
    jam = JamMap()
    areas = (WatchedArea("black_sea", "Black Sea"),)
    sleeps: list[float] = []

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        await asyncio.sleep(0)

    monitor = AviationMonitor(store, jam, sink, FakeClock(NOW), areas, sleep=sleep)
    assert await monitor.sample() == 7
    hour = NOW.replace(minute=0, second=0, microsecond=0)
    samples = {sample for _, sample in sink.rows}
    assert ("military_aircraft", "UA", 6) in samples
    assert ("area_aircraft", "black_sea", 1) in samples and (
        "emergency_squawks",
        "all",
        1,
    ) in samples
    assert all(when == hour for when, _ in sink.rows)
    assert samples_for([], areas) == [
        ("area_aircraft", "black_sea", 0),
        ("emergency_squawks", "all", 0),
    ]

    await monitor.start()
    await monitor.start()  # idempotent
    for _ in range(20):
        await asyncio.sleep(0)
    await monitor.stop()
    assert sleeps and sleeps[0] == 300.0
    assert len(sink.rows) > 4


async def test_aviation_board_and_jamming_api(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    now = container.clock.now()
    container.store.upsert(fleet(now))
    await container.aviation_monitor.sample()
    async with container.session_factory() as session:
        baselines = container.repositories(session).baselines
        hour = now.replace(minute=0, second=0, microsecond=0)
        await baselines.record("military_aircraft", "UA", hour - timedelta(hours=1), 3)
        await baselines.record("military_aircraft", "UA", hour - timedelta(hours=1), 2)  # keeps 3
        await session.commit()

    board = await client.get("/api/trackers/aviation", headers=bearer(token))
    assert board.status_code == 200, board.text
    data = board.json()
    assert data["military_total"] == 6 and data["jam_red"] == 1 and data["jam_amber"] == 0
    ukraine = data["by_country"][0]
    assert ukraine["iso"] == "UA" and ukraine["count"] == 6
    assert ukraine["baseline"] == 4.5 and ukraine["ratio"] == 1.33  # mean of 3 and 6
    assert data["emergencies"][0]["title"] == "Aircraft sos"
    black_sea = next(area for area in data["areas"] if area["id"] == "black_sea")
    assert black_sea["count"] == 1 and black_sea["baseline"] == 1.0
    assert data["jam_updated_at"] is not None

    jamming = await client.get("/api/trackers/aviation/jamming", headers=bearer(token))
    assert jamming.status_code == 200
    cells = jamming.json()["cells"]
    assert len(cells) == 1 and cells[0]["level"] == "red" and cells[0]["percent_bad"] == 16.7
    assert (await client.get("/api/trackers/aviation")).status_code == 401


async def test_aviation_report_carries_the_board_as_background(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await client.post("/api/admin/llm/profiles", json=PROFILE, headers=bearer(admin_token))
    now = container.clock.now()
    container.store.upsert(fleet(now))
    await container.aviation_monitor.sample()
    judgements = good_body()["key_judgements"]
    fits = good_body(
        key_judgements=[judgements[0], {**judgements[1], "supporting_evidence": ["E2"]}]
    )
    gateway = ScriptedGateway(json.dumps(fits))
    container.llm = gateway
    created = await client.post(
        "/api/reports", json={"template": "aviation_activity"}, headers=bearer(token)
    )
    assert created.status_code == 201, created.text
    assert created.json()["report"]["title"] == "Aviation activity report: global"
    prompt = gateway.requests[0].messages[1].content
    assert "Military aircraft tracked now: 6" in prompt and "GNSS interference cells" in prompt
    assert len(created.json()["version"]["evidence"]) == 8
    board = container.aviation().board({"UA": 5.0}, {})
    assert "UA 6 (baseline 5.0)" in summary_text(board)
