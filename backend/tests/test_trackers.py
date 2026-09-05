"""Trackers: hazard and conflict cards from the live store, the curated list, and the API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from ase.adapters.geo.conflicts import ConflictIndex, _conflict
from ase.container import Container
from ase.domain.events import Category
from ase.domain.trackers import (
    Hazard,
    activity,
    conflict_card,
    hazard_cards,
    hazard_of,
    timeline,
)
from ase.domain.users import User
from feeds_helpers import NOW, make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from tracker_helpers import UKRAINE, conflict_events, disaster_events


def test_activity_timeline_and_hazard_folding() -> None:
    events = conflict_events()[:3]
    counts = activity(events, NOW)
    assert (counts.last_24h, counts.last_7d, counts.previous_7d) == (1, 2, 1)
    assert counts.trend == 2.0
    assert activity([], NOW).trend is None
    buckets = timeline(events, NOW)
    assert len(buckets) == 14 and buckets[-1].day == NOW.date()
    assert buckets[-1].count == 1 and buckets[-4].count == 1 and buckets[-4].max_severity == 0.9
    assert hazard_of(make_event("a", subtype="earthquakes")) is Hazard.EARTHQUAKE
    assert hazard_of(make_event("b", subtype="landslides")) is Hazard.OTHER
    assert hazard_of(make_event("c", category=Category.NEWS, subtype="article")) is None


def test_cards_summarise_hazards_and_conflicts() -> None:
    cards = hazard_cards(disaster_events(), NOW)
    # Equal activity: more red alerts first, then the hazard name.
    assert [card.hazard for card in cards[:2]] == [Hazard.EARTHQUAKE, Hazard.VOLCANO]
    assert {card.hazard for card in cards if card.activity.last_7d == 1} == {
        Hazard.EARTHQUAKE,
        Hazard.VOLCANO,
        Hazard.TROPICAL_CYCLONE,
        Hazard.OTHER,
    }
    quakes = cards[0]
    assert quakes.activity.last_7d == 1 and quakes.activity.previous_7d == 1
    assert quakes.red_alerts == 1 and quakes.max_severity == 0.9 and quakes.countries == ("JP",)
    assert quakes.top is not None and quakes.top.title == "M6.1 quake"
    volcano = cards[1]
    assert volcano.red_alerts == 1  # tagged red by GDACS even with no severity
    assert len(cards) == len(Hazard)

    card = conflict_card(UKRAINE, conflict_events()[:4], NOW)
    assert card.activity.last_7d == 2 and card.reporting_7d == 1 and card.fatalities_7d == 4
    assert card.top is not None and card.top.title == "Drone strike near Sumy"
    assert card.latest is not None and card.latest.title == "Shelling in Kharkiv"


def test_conflict_list_loads_and_rejects_bad_rows() -> None:
    index = ConflictIndex.from_resource()
    assert len(index.all()) >= 20
    ukraine = index.get("ukraine")
    assert ukraine is not None and "UA" in ukraine.countries and ukraine.status == "war"
    assert index.get("nope") is None
    with pytest.raises(ValueError, match="bounding box"):
        _conflict({"id": "x", "bbox": [0, 0, 0]})
    with pytest.raises(ValueError, match="out of range"):
        _conflict({"id": "x", "bbox": [0, 10, 0, -10]})
    with pytest.raises(ValueError, match="status"):
        _conflict({"id": "x", "bbox": [0, 0, 1, 1], "status": "hot"})
    with pytest.raises(ValueError, match="no id"):
        _conflict({"bbox": [0, 0, 1, 1]})
    with pytest.raises(ValueError, match="Duplicate"):
        ConflictIndex([UKRAINE, UKRAINE])


async def test_tracker_api_boards_and_details(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    now = container.clock.now()
    container.store.upsert([*conflict_events(now), *disaster_events(now)])

    disasters = await client.get("/api/trackers/disasters", headers=bearer(token))
    assert disasters.status_code == 200
    items = disasters.json()["items"]
    assert items[0]["hazard"] == "earthquake" and items[0]["title"] == "Earthquakes"
    assert items[0]["activity"] == {
        "last_24h": 1,
        "last_7d": 1,
        "previous_7d": 1,
        "trend": 1.0,
    }
    assert items[0]["top"]["title"] == "M6.1 quake"

    quakes = await client.get("/api/trackers/disasters/earthquake", headers=bearer(token))
    assert quakes.status_code == 200
    detail = quakes.json()
    assert len(detail["timeline"]) == 14 and detail["timeline"][-1]["count"] == 1
    assert [event["title"] for event in detail["events"]] == ["M6.1 quake", "M4.5 quake"]
    assert (
        await client.get("/api/trackers/disasters/plague", headers=bearer(token))
    ).status_code == 422

    conflicts = await client.get("/api/trackers/conflicts", headers=bearer(token))
    assert conflicts.status_code == 200
    board = conflicts.json()["items"]
    assert board[0]["conflict"]["id"] == "ukraine"
    assert board[0]["activity"]["last_7d"] == 2 and board[0]["reporting_7d"] == 1
    assert board[0]["fatalities_7d"] == 4
    sudan = next(card for card in board if card["conflict"]["id"] == "sudan")
    assert sudan["activity"]["last_7d"] == 1
    assert board[-1]["activity"]["last_7d"] == 0 and board[-1]["latest"] is None

    ukraine = await client.get("/api/trackers/conflicts/ukraine", headers=bearer(token))
    assert ukraine.status_code == 200
    detail = ukraine.json()
    assert detail["card"]["conflict"]["bbox"] == [22.0, 44.0, 41.0, 52.5]
    assert [event["title"] for event in detail["events"]] == [
        "Shelling in Kharkiv",
        "Talks in Kyiv",
        "Drone strike near Sumy",
        "Last week's clash",
    ]
    assert sum(bucket["count"] for bucket in detail["timeline"]) == 3
    assert (
        await client.get("/api/trackers/conflicts/nope", headers=bearer(token))
    ).status_code == 404
    assert (await client.get("/api/trackers/conflicts")).status_code == 401
