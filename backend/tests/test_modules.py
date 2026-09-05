"""The maritime, space and cyber boards and the two templates that use them as background."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from httpx import AsyncClient

from ase.application.trackers.modules import cyber_summary, maritime_summary
from ase.container import Container
from ase.domain.events import Category, Event, Point
from ase.domain.users import User
from feeds_helpers import NOW, make_event
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_helpers import PROFILE, ScriptedGateway, good_body


def module_events(now: datetime = NOW) -> list[Event]:
    warning = make_event(
        "w1",
        source_id="nga_navarea",
        category=Category.MARITIME,
        subtype="navarea_warning",
        title="NAVAREA 4 2026/1: GUNNERY EXERCISE",
        point=Point(-76.5, 39.2),
        severity=0.6,
        published_at=now - timedelta(hours=2),
    ).with_changes(attributes={"nav_area": "4", "kind": "military_exercise", "positions": 1})
    warning2 = make_event(
        "w2",
        source_id="nga_navarea",
        category=Category.MARITIME,
        subtype="navarea_warning",
        title="NAVAREA P 2026/9: LIGHT UNLIT",
        point=None,
        severity=0.3,
        published_at=now - timedelta(days=3),
    ).with_changes(attributes={"nav_area": "P", "kind": "hazard", "positions": 0})
    station = make_event(
        "iss",
        source_id="celestrak_stations",
        category=Category.SPACE,
        subtype="satellite",
        title="ISS (ZARYA)",
        point=Point(10.0, 20.0),
        published_at=now,
    )
    launch = make_event(
        "l1",
        source_id="launch_library",
        category=Category.SPACE,
        subtype="launch",
        title="Launch: Spectrum",
        point=Point(15.6, 69.1),
        published_at=now - timedelta(hours=1),
    ).with_changes(attributes={"net": (now + timedelta(days=2)).isoformat()})
    old_launch = launch.with_changes(
        id="l0",
        title="Launch: Old",
        attributes={"net": (now - timedelta(days=3)).isoformat()},
    )
    kp = make_event(
        "kp",
        source_id="swpc_kp",
        category=Category.SPACE,
        subtype="geomagnetic",
        title="Planetary K index 5.33: storm",
        point=None,
        published_at=now,
    ).with_changes(attributes={"kp": 5.33}, tags=frozenset({"geomagnetic", "storm"}))
    alert = make_event(
        "sw",
        source_id="swpc_alerts",
        category=Category.SPACE,
        subtype="space_weather",
        title="Geomagnetic storm watch",
        point=None,
        published_at=now - timedelta(hours=3),
    )
    outage = make_event(
        "o1",
        source_id="ioda_outages",
        category=Category.CYBER,
        subtype="outage",
        title="Internet outage signal: Tunisia",
        point=None,
        country_iso="TN",
        severity=0.8,
        published_at=now - timedelta(hours=5),
    )
    claim = make_event(
        "r1",
        source_id="ransomware_live",
        category=Category.CYBER,
        subtype="ransomware",
        title="Paylogix: claimed by akira",
        point=None,
        country_iso="US",
        severity=0.5,
        published_at=now - timedelta(days=1),
    ).with_changes(attributes={"group": "akira"})
    kev = make_event(
        "k1",
        source_id="cisa_kev",
        category=Category.CYBER,
        subtype="kev",
        title="CVE-2026-0001 added to KEV",
        point=None,
        published_at=now - timedelta(days=2),
    )
    return [warning, warning2, station, launch, old_launch, kp, alert, outage, claim, kev]


async def test_module_boards(client: AsyncClient, container: Container, user: User) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    now = container.clock.now()
    container.store.upsert(module_events(now))

    maritime = (await client.get("/api/trackers/maritime", headers=bearer(token))).json()
    assert maritime["warnings_total"] == 2 and maritime["located"] == 1
    assert maritime["by_area"] == [
        {"key": "4", "count": 1, "max_severity": 0.6},
        {"key": "P", "count": 1, "max_severity": 0.3},
    ]
    assert maritime["by_kind"][0]["key"] in ("hazard", "military_exercise")
    assert [e["title"] for e in maritime["notable"]] == ["NAVAREA 4 2026/1: GUNNERY EXERCISE"]
    assert len(maritime["latest"]) == 2

    space = (await client.get("/api/trackers/space", headers=bearer(token))).json()
    assert [e["title"] for e in space["stations"]] == ["ISS (ZARYA)"]
    assert [e["title"] for e in space["launches"]] == ["Launch: Spectrum"]
    assert space["kp"] == 5.33 and space["kp_level"] == "storm" and space["alerts_24h"] == 1

    cyber = (await client.get("/api/trackers/cyber", headers=bearer(token))).json()
    assert cyber["outages_24h"] == 1 and cyber["outages_by_country"][0]["key"] == "TN"
    assert cyber["ransomware_7d"] == 1 and cyber["ransomware_by_group"][0]["key"] == "akira"
    assert cyber["kev_7d"] == 1 and cyber["latest_kev"][0]["title"].startswith("CVE-2026-0001")
    assert (await client.get("/api/trackers/cyber")).status_code == 401

    boards = container.modules()
    assert "NAVAREA 4 1" in maritime_summary(boards.maritime_board())
    assert "akira 1" in cyber_summary(boards.cyber_board())


async def test_maritime_and_cyber_reports_take_the_board_as_background(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await client.post("/api/admin/llm/profiles", json=PROFILE, headers=bearer(admin_token))
    container.store.upsert(module_events(container.clock.now()))
    judgements = good_body()["key_judgements"]
    fits = good_body(
        key_judgements=[judgements[0], {**judgements[1], "supporting_evidence": ["E2"]}]
    )
    for template, phrase in (
        ("maritime_activity", "Active broadcast warnings in the last fortnight: 2"),
        ("cyber_summary", "Ransomware claims in the last week: 1"),
    ):
        gateway = ScriptedGateway(json.dumps(fits))
        container.llm = gateway
        created = await client.post(
            "/api/reports", json={"template": template}, headers=bearer(token)
        )
        assert created.status_code == 201, created.text
        assert phrase in gateway.requests[0].messages[1].content
