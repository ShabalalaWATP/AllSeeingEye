"""No-live-network route parsing, admission and current-session boundaries."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest

from ase.adapters.routing.valhalla import ValhallaRoutingGateway, parse_route
from ase.application.navigation import RoutePlanner
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.events import Point
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

WAYPOINTS = (Point(0, 0), Point(0.01, 0.01))
BODY = {"mode": "walking", "waypoints": [{"lat": 0, "lon": 0}, {"lat": 0.01, "lon": 0.01}]}


def payload():
    return {
        "trip": {
            "status": 0,
            "units": "kilometers",
            "summary": {"length": 2, "time": 600},
            "legs": [
                {
                    "shape": "??_pR_pR",
                    "maneuvers": [{"instruction": "Continue east.", "length": 2, "time": 600}],
                }
            ],
        }
    }


def test_real_polyline6_decoding_and_directions():
    result = parse_route(json.dumps(payload()).encode(), "walking", 2)
    assert result.coordinates == WAYPOINTS
    assert result.distance_km == 2 and result.steps[0].instruction == "Continue east."


@pytest.mark.parametrize(
    "mutation",
    [
        lambda trip: trip.update(status=True),
        lambda trip: trip.update(units="miles"),
        lambda trip: trip.update(legs=[]),
        lambda trip: trip["legs"][0].update(shape="~" * 20),
        lambda trip: trip["legs"][0].update(shape="?"),
        lambda trip: trip["summary"].update(length=float("nan")),
        lambda trip: trip["legs"][0]["maneuvers"][0].update(instruction="x" * 501),
        lambda trip: trip["legs"][0]["maneuvers"][0].update(time=True),
    ],
)
def test_malformed_provider_output_rejected(mutation):
    value = payload()
    mutation(value["trip"])
    with pytest.raises(ValueError):
        parse_route(json.dumps(value).encode(), "walking", 2)


async def test_fixed_origin_costing_protected_transport_and_no_retry():
    http = Mock()
    http.get_secret_bytes = AsyncMock(return_value=json.dumps(payload()).encode())
    gateway = ValhallaRoutingGateway(http)
    await gateway.route("cycling", WAYPOINTS)
    target = http.get_secret_bytes.call_args.args[0]
    url = urlsplit(target.url)
    assert (
        url.scheme == "https"
        and url.netloc == "valhalla1.openstreetmap.de"
        and url.path == "/route"
    )
    assert "0.01" not in repr(target)
    decoded = json.loads(parse_qs(url.query)["json"][0])
    assert decoded["costing"] == "bicycle" and decoded["shape_format"] == "polyline6"
    assert decoded["locations"][1] == {"lat": 0.01, "lon": 0.01, "type": "break"}
    assert http.get_secret_bytes.await_count == 1


async def test_admission_single_flight_and_cancel_releases_slot():
    entered = asyncio.Event()
    finish = asyncio.Event()

    async def blocked(*args):
        entered.set()
        await finish.wait()
        return parse_route(json.dumps(payload()).encode(), "walking", 2)

    gateway = Mock()
    gateway.route = AsyncMock(side_effect=blocked)
    limiter = Mock()
    limiter.hit.return_value = None
    planner = RoutePlanner(gateway, limiter)
    task = asyncio.create_task(planner.calculate(uuid4(), "walking", WAYPOINTS))
    await entered.wait()
    with pytest.raises(RateLimited):
        await planner.calculate(uuid4(), "walking", WAYPOINTS)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    finish.set()
    assert (await planner.calculate(uuid4(), "walking", WAYPOINTS)).distance_km == 2
    assert gateway.route.await_count == 2


async def test_bounds_and_rate_before_provider_and_redacted_failure():
    gateway = Mock()
    gateway.route = AsyncMock(side_effect=RuntimeError("private coordinates"))
    limiter = Mock()
    limiter.hit.return_value = None
    planner = RoutePlanner(gateway, limiter)
    with pytest.raises(InvalidRequest):
        await planner.calculate(uuid4(), "walking", (Point(0, 0), Point(80, 0)))
    gateway.route.assert_not_called()
    limiter.hit.return_value = 20
    with pytest.raises(RateLimited):
        await planner.calculate(uuid4(), "walking", WAYPOINTS)
    gateway.route.assert_not_called()
    limiter.hit.return_value = None
    with pytest.raises(InvalidRequest, match="Route unavailable") as error:
        await planner.calculate(uuid4(), "walking", WAYPOINTS)
    assert "private coordinates" not in str(error.value)


async def test_route_api_authenticated_bounded_and_rechecks_logout(
    client, container, user, monkeypatch
):
    monkeypatch.setattr(
        container,
        "settings",
        container.settings.model_copy(update={"feeds_contact": "operator@example.org"}),
    )
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    gateway = Mock()
    gateway.route = AsyncMock(
        return_value=parse_route(json.dumps(payload()).encode(), "walking", 2)
    )
    limiter = Mock()
    limiter.hit.return_value = None
    monkeypatch.setattr(container, "route_planner", RoutePlanner(gateway, limiter))
    assert (await client.post("/api/navigation/route", json=BODY)).status_code == 401
    assert (
        await client.post("/api/navigation/route", json={**BODY, "mode": "flying"}, headers=headers)
    ).status_code == 422
    oversized = await client.post(
        "/api/navigation/route",
        content=b" " * 4097,
        headers={**headers, "Content-Type": "application/json"},
    )
    assert oversized.status_code == 422
    gateway.route.assert_not_called()
    result = await client.post("/api/navigation/route", json=BODY, headers=headers)
    assert result.status_code == 200 and result.json()["coordinates"] == [[0, 0], [0.01, 0.01]]
    assert result.headers["cache-control"] == "private, no-store"

    async def logout(*args):
        async with container.session_factory() as session:
            await container.repositories(session).refresh_tokens.revoke_family(
                container.issuer.verify(token).family_id, container.clock.now()
            )
            await session.commit()
        return parse_route(json.dumps(payload()).encode(), "walking", 2)

    gateway.route.side_effect = logout
    assert (
        await client.post("/api/navigation/route", json=BODY, headers=headers)
    ).status_code == 401


@pytest.mark.parametrize(
    "contact", ["", "not-an-email", "operator@example.invalid", "operator@example.test"]
)
async def test_placeholder_contact_blocks_routes_before_provider(
    client, container, user, monkeypatch, contact
):
    monkeypatch.setattr(
        container, "settings", container.settings.model_copy(update={"feeds_contact": contact})
    )
    calculate = AsyncMock()
    monkeypatch.setattr(container.route_planner, "calculate", calculate)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    capability = await client.get("/api/navigation/capabilities", headers=headers)
    assert capability.status_code == 200
    assert capability.json()["available"] is False
    assert "ASE_FEEDS_CONTACT" in capability.json()["configuration_message"]
    assert capability.json()["operator_contact"] == ""
    response = await client.post("/api/navigation/route", json=BODY, headers=headers)
    assert response.status_code == 422
    calculate.assert_not_called()
