"""Confirmed losses, civilian harm, lens series and the flagged frontline providers."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from httpx import AsyncClient

from ase.adapters.feeds.ukraine_frontline import (
    FrontlineProviders,
    parse_deepstate,
    parse_ocha,
    parse_spotted,
)
from ase.adapters.geo import ukraine_casualties_import as casualties
from ase.adapters.geo import ukraine_losses_import as losses
from ase.adapters.geo.ukraine_figures import (
    load_civilian_harm,
    load_confirmed_losses,
    parse_casualties,
    parse_losses,
)
from ase.application.ukraine import UkraineBoardService, UpdateEntry, lens_series
from ase.container import Container
from ase.domain.ukraine.confirmed import CivilianHarm, ConfirmedLosses, LossRow, loss_group
from ase.domain.ukraine.frontline import FrontlineStatus
from ase.domain.ukraine.lenses import Lens
from ase.domain.ukraine.reference import Side
from ase.domain.ukraine.updates import UpdateGroup
from ase.domain.users import User
from feeds_helpers import NOW, FakeClock, FakeHttp, make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

ORYX_CSV = (
    '"","country","equipment_type","destroyed","abandoned","captured","damaged","type_total","row_id","Date"\n'
    '"1","Russia","All Types",100,5,10,3,118,1,"{day}"\n'
    '"2","Russia","Losses of Armoured Combat Vehicles [Tanks, AFVs] - 50, of which: '
    'destroyed: 40",40,3,5,2,50,2,"{day}"\n'
    '"3","Russia","Tanks",30,1,2,1,34,3,"{day}"\n'
    '"4","Ukraine","All Types",60,2,4,1,67,4,"{day}"\n'
    '"5","Ukraine","Surface-To-Air Missile Systems\n",7,0,1,0,8,5,"{day}"\n'
)


def oryx_client(available: set[str]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        day = str(request.url).rsplit("/", 1)[-1].removesuffix(".csv")
        if day in available:
            return httpx.Response(200, text=ORYX_CSV.replace("{day}", day))
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_oryx_import_keeps_plain_types_and_a_month_of_totals() -> None:
    today = date(2026, 9, 13)
    available = {(today - timedelta(days=n)).isoformat() for n in (1, 2, 5)}
    with oryx_client(available) as client:
        snapshot = losses.build_snapshot(client, today, NOW)
    assert snapshot["recorded_on"] == "2026-09-12"
    rows = snapshot["rows"]
    assert [(r["side"], r["equipment_type"], r["group"]) for r in rows] == [
        ("ru", "All Types", "total"),
        ("ru", "Tanks", "tanks"),
        ("ua", "All Types", "total"),
        ("ua", "Surface-To-Air Missile Systems", "air_defence"),
    ]
    assert len(snapshot["days"]) == 6 and snapshot["days"][0]["on"] == "2026-09-08"
    parsed = parse_losses(json.loads(json.dumps(snapshot)))
    assert parsed.total(Side.RU) is not None and parsed.total(Side.RU).total == 118
    assert loss_group("Trucks and similar vehicles") == "other"
    with oryx_client(set()) as client, pytest.raises(ValueError, match="lookback"):
        losses.build_snapshot(client, today, NOW)


HRMMU_LISTING = (
    '<a href="/en/Protection-of-Civilians-in-Armed-Conflict-July-2026">July</a>'
    '<a href="/en/Protection-of-Civilians-in-Armed-Conflict-June-2026">June</a>'
    '<a href="/en/Protection-of-Civilians-in-Armed-Conflict-July-2026">again</a>'
    '<a href="/en/Protection-of-Civilians-in-Armed-Conflict-Smarch-2026">bad</a>'
)


def hrmmu_page(month: str, sentence: str) -> str:
    return (
        f"<html><head><title>Protection of Civilians in Armed Conflict — {month} | HRMMU</title>"
        '</head><body><time datetime="2026-08-12T16:00:21+03:00">12 August</time>'
        f"<p>Summary {sentence}</p></body></html>"
    )


def test_hrmmu_listing_and_month_pages_parse_the_fixed_sentence() -> None:
    listing = casualties.parse_listing(HRMMU_LISTING)
    assert [month for _, month in listing] == [date(2026, 7, 1), date(2026, 6, 1)]
    july = casualties.parse_month(
        hrmmu_page(
            "July 2026",
            "At least 437 civilians were killed and 2,610 injured in Ukraine in July 2026, a rise.",
        ),
        date(2026, 7, 1),
        "https://x/july",
    )
    assert july["killed"] == 437 and july["injured"] == 2610
    assert july["published_on"] == "2026-08-12" and july["title"].startswith("Protection")
    june = casualties.parse_month(
        hrmmu_page("June 2026", "Different wording this month."), date(2026, 6, 1), "https://x/june"
    )
    assert june["killed"] is None and june["injured"] is None
    wrong = casualties.parse_month(
        hrmmu_page(
            "June 2026", "At least 1 civilian was killed and 2 injured in Ukraine in May 2026."
        ),
        date(2026, 6, 1),
        "https://x/june",
    )
    assert wrong["killed"] is None


def test_hrmmu_import_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("protection-of-civilians"):
            return httpx.Response(200, text=HRMMU_LISTING)
        month = "July 2026" if "July" in url else "June 2026"
        return httpx.Response(
            200,
            text=hrmmu_page(
                month, f"At least 10 civilians were killed and 20 injured in Ukraine in {month}."
            ),
        )

    real = httpx.Client
    monkeypatch.setattr(
        casualties.httpx,
        "Client",
        lambda **kw: real(transport=httpx.MockTransport(handler), headers=kw.get("headers")),
    )
    destination = tmp_path / "casualties.json"
    assert casualties.import_ukraine_casualties(str(destination)) == 2
    harm = parse_casualties(json.loads(destination.read_text("utf-8")))
    assert harm.latest is not None and harm.latest.month == date(2026, 7, 1)
    assert {r.basis for r in harm.references} <= {"documented", "claimed", "reported"}


def test_packaged_figures_load() -> None:
    confirmed = load_confirmed_losses()
    harm = load_civilian_harm()
    assert confirmed is not None and harm is not None
    assert confirmed.total(Side.RU) is not None and confirmed.total(Side.UA) is not None
    assert confirmed.days and "Oryx" in confirmed.attribution
    assert harm.latest is not None and harm.latest.killed is not None
    assert any(r.id == "kiel-support-tracker" for r in harm.references)


def test_confirmed_and_harm_bounds() -> None:
    row = LossRow(Side.RU, "All Types", "total", 1, 0, 0, 0)
    with pytest.raises(ValueError, match="bound"):
        ConfirmedLosses(date(2026, 9, 1), NOW, "a", "l", "https://x", (), ())
    with pytest.raises(ValueError, match="negative"):
        ConfirmedLosses(
            date(2026, 9, 1),
            NOW,
            "a",
            "l",
            "https://x",
            (LossRow(Side.RU, "T", "t", -1, 0, 0, 0),),
            (),
        )
    assert (
        ConfirmedLosses(date(2026, 9, 1), NOW, "a", "l", "https://x", (row,), ()).total(Side.UA)
        is None
    )
    assert CivilianHarm(NOW, "https://x", "a", (), ()).latest is None
    with pytest.raises(ValueError, match="basis"):
        parse_casualties(
            {
                "retrieved_at": "2026-09-13T00:00:00+00:00",
                "source_url": "https://x",
                "attribution": "a",
                "months": [],
                "references": [
                    {
                        "id": "r",
                        "label": "l",
                        "text": "t",
                        "basis": "guess",
                        "url": "https://x",
                        "as_of": "2026-01-01",
                    }
                ],
            }
        )


def test_lens_series_counts_items_per_day_and_group() -> None:
    now = datetime(2026, 9, 13, 12, tzinfo=UTC)
    entries = [
        UpdateEntry(
            make_event("a", source_id="kyiv_independent", published_at=now - timedelta(days=1)),
            UpdateGroup.UKRAINIAN,
            frozenset({Lens.EQUIPMENT, Lens.STRIKES}),
        ),
        UpdateEntry(
            make_event("b", source_id="bbc_world", published_at=now - timedelta(days=30)),
            UpdateGroup.INTERNATIONAL,
            frozenset({Lens.EQUIPMENT}),
        ),
    ]
    series = {item.lens: item for item in lens_series(entries, now)}
    equipment = series[Lens.EQUIPMENT]
    assert len(equipment.days) == 14 and equipment.days[-1] == now.date()
    assert equipment.groups[UpdateGroup.UKRAINIAN][-2] == 1
    assert sum(equipment.groups[UpdateGroup.INTERNATIONAL]) == 0
    assert sum(series[Lens.WORKFORCE].groups[UpdateGroup.UKRAINIAN]) == 0


DEEPSTATE = {
    "id": 1,
    "datetime": "12.09 o 21:04",
    "map": {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Окуповано /// Occupied /// geoJSON.status.occupied"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[37.0, 48.0], [37.1, 48.0], [37.1, 48.1], [37.0, 48.0]]],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Крим /// Occupied Crimea /// geoJSON.territories.crimea"},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [[[[33.0, 45.0], [34.0, 45.0], [34.0, 46.0], [33.0, 45.0]]]],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Напрямок удару /// Direction of attack"},
                "geometry": {"type": "Point", "coordinates": [37.0, 48.0]},
            },
        ],
    },
}
OCHA = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"date": 1788912000000, "source": "ISW"},
            "geometry": {"type": "LineString", "coordinates": [[37.0, 48.0], [37.2, 48.3]]},
        },
        {
            "type": "Feature",
            "properties": {"date": 1788000000000},
            "geometry": {"type": "MultiLineString", "coordinates": [[[36.0, 47.0], [36.1, 47.1]]]},
        },
    ],
}
SPOTTED = {
    "losses": [
        {
            "id": 1,
            "type": "Tanks",
            "model": "T-72B3",
            "status": "Destroyed",
            "lost_by": "Russia",
            "date": "2026-09-10",
            "nearest_location": "Pokrovsk",
            "geo": "48.28,37.17",
        },
        {
            "id": 2,
            "type": "Transport",
            "model": "Ural",
            "status": "Destroyed",
            "lost_by": "Russia",
            "date": "2026-09-10",
            "nearest_location": "Belgorod",
            "geo": None,
        },
        {
            "id": 3,
            "type": "Tanks",
            "model": "T-80",
            "status": "Damaged",
            "lost_by": "Russia",
            "date": "bad",
            "geo": "1,2",
        },
        {
            "id": 4,
            "type": "Tanks",
            "model": "T-90",
            "status": "Damaged",
            "lost_by": "Russia",
            "date": "2026-09-11",
            "geo": "999,2",
        },
    ]
}


def test_provider_parsers_keep_classified_geometry_only() -> None:
    assessed, features = parse_deepstate(DEEPSTATE)
    assert assessed == "12.09 o 21:04"
    assert [(f.kind.value, f.label) for f in features] == [
        ("occupied", "Occupied"),
        ("historical", "Occupied Crimea"),
    ]
    assessed, ocha = parse_ocha(OCHA)
    expected = datetime.fromtimestamp(1788912000, tz=UTC).date().isoformat()
    assert assessed == expected and ocha[0].kind.value == "line" and len(ocha[0].lines) == 2
    assert parse_ocha({"features": []}) == (None, ())
    spotted = parse_spotted(SPOTTED)
    assert [loss.id for loss in spotted] == [1]
    with pytest.raises(Exception, match="invalid"):
        parse_deepstate({"map": {}})


async def test_providers_are_disabled_by_default_and_cache_when_enabled() -> None:
    clock = FakeClock(NOW)
    off = FrontlineProviders(FakeHttp(), clock, deepstate=False, ocha=False, spotted=False)  # type: ignore[arg-type]
    state = await off.snapshot()
    assert state.status is FrontlineStatus.DISABLED and "permission" in state.reason
    assert (await off.spotted()).status is FrontlineStatus.DISABLED

    http = FakeHttp({"deepstatemap": DEEPSTATE, "warspotting": SPOTTED})
    on = FrontlineProviders(http, clock, deepstate=True, ocha=False, spotted=True)  # type: ignore[arg-type]
    first = await on.snapshot()
    assert first.status is FrontlineStatus.READY and first.snapshot is not None
    assert first.snapshot.provider == "deepstate" and len(first.snapshot.features) == 2
    assert (await on.snapshot()) is first and len(http.requests) == 1
    spotted = await on.spotted()
    # One documented recent call; the entry without coordinates is not mappable.
    assert spotted.status is FrontlineStatus.READY and len(spotted.losses) == 1
    assert len(http.requests) == 2
    clock.advance(timedelta(hours=7))
    http.payloads = {}
    stale = await on.snapshot()
    assert stale.status is FrontlineStatus.STALE and stale.snapshot is first.snapshot
    assert (await on.spotted()).status is FrontlineStatus.STALE

    ocha = FrontlineProviders(FakeHttp(), FakeClock(NOW), deepstate=False, ocha=True, spotted=False)  # type: ignore[arg-type]
    assert (await ocha.snapshot()).status is FrontlineStatus.UNAVAILABLE


async def test_board_and_endpoints_carry_figures_and_provider_states(
    client: AsyncClient, container: Container, user: User
) -> None:
    service: UkraineBoardService = container.ukraine()
    board = service.board()
    assert board.confirmed is not None and board.civilian_harm is not None
    assert len(board.lens_series) == 5
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/conflicts/ukraine", headers=bearer(token))
    body = response.json()
    assert body["confirmed"]["rows"][0]["side"] in ("ru", "ua")
    assert body["civilian_harm"]["references"] and body["lens_series"][0]["lens"] == "equipment"
    frontline = await client.get("/api/conflicts/ukraine/frontline", headers=bearer(token))
    assert frontline.status_code == 200 and frontline.json()["status"] == "disabled"
    assert frontline.headers["cache-control"] == "private, max-age=900"
    spotted = await client.get("/api/conflicts/ukraine/spotted", headers=bearer(token))
    assert spotted.status_code == 200 and spotted.json()["losses"] == []
    assert (await client.get("/api/conflicts/ukraine/frontline")).status_code == 401
