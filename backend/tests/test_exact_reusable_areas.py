"""Saved areas and warning rules retain exact bounded geometry, including holes."""

from dataclasses import replace
from uuid import uuid4

import pytest

from ase.adapters.store.query import select_events
from ase.application.direction.areas import AoiInput, build_area
from ase.application.ports.feeds import EventQuery
from ase.domain.area_membership import area_contains_event
from ase.domain.events import GeoConfidence, Point
from ase.domain.research_area import area_to_dict
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_research_area import area
from test_warning import NOW, indicator
from tracker_helpers import conflict_events


def triangle():
    return area([[[10, 40], [12, 40], [10, 42], [10, 40]]])


def event(lon, lat, **changes):
    return replace(
        conflict_events(NOW)[0],
        point=Point(lon, lat),
        geo_confidence=GeoConfidence.EXACT,
        **changes,
    )


def test_exact_area_excludes_envelope_and_approximate_points_before_limit(user):
    saved = build_area(
        AoiInput(name="Triangle", kind="geometry", research_area=triangle()), user, uuid4(), NOW
    )
    inside, outside = event(10.2, 40.2, id="inside"), event(11.8, 41.8, id="outside")
    assert saved.contains(inside)
    assert not saved.contains(outside)
    assert not saved.contains(replace(inside, geo_confidence=GeoConfidence.COUNTRY))
    assert select_events([outside, inside], EventQuery(research_area=triangle(), limit=1)) == [
        inside
    ]
    rule = indicator(countries=(), keywords=(), categories=(), research_area=triangle())
    assert rule.matches(inside) and not rule.matches(outside)


def test_exact_area_hole_boundary_and_dateline_components():
    polygon = area(
        [
            [[10, 40], [14, 40], [14, 44], [10, 44], [10, 40]],
            [[11, 41], [12, 41], [12, 42], [11, 42], [11, 41]],
        ]
    )
    assert not area_contains_event(polygon, event(11.5, 41.5))
    assert area_contains_event(polygon, event(11, 41))
    split = area(
        [
            [[[170, -10], [180, -10], [180, 10], [170, 10], [170, -10]]],
            [[[-180, -10], [-170, -10], [-170, 10], [-180, 10], [-180, -10]]],
        ],
        kind="MultiPolygon",
    )
    assert area_contains_event(split, event(175, 0))
    assert area_contains_event(split, event(-175, 0))
    assert not area_contains_event(split, event(0, 0))


@pytest.mark.parametrize("route", ["/api/direction/aois", "/api/warning/indicators"])
async def test_exact_area_api_round_trip(client, user, route):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    payload = {
        "name": "Exact triangle",
        "research_area": {"geometry": triangle().geometry.to_collection()},
    }
    if route.endswith("aois"):
        payload["kind"] = "geometry"
    response = await client.post(route, json=payload, headers=bearer(token))
    assert response.status_code == 201, response.text
    assert response.json()["research_area"] == area_to_dict(triangle())
    listed = await client.get(route, headers=bearer(token))
    assert listed.json()["items"][0]["research_area"] == area_to_dict(triangle())


@pytest.mark.parametrize("route", ["/api/direction/aois", "/api/warning/indicators"])
async def test_exact_area_rejects_conflicting_envelopes_and_invalid_shapes(client, user, route):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    body = {"name": "Area", "research_area": {"geometry": triangle().geometry.to_collection()}}
    if route.endswith("aois"):
        body["kind"] = "geometry"
    rejected = await client.post(
        route, json={**body, "bbox": [0, 0, 50, 50]}, headers=bearer(token)
    )
    assert rejected.status_code == 422
    body["research_area"]["geometry"]["features"][0]["geometry"]["coordinates"] = [
        [[10, 40], [12, 42], [12, 40], [10, 42], [10, 40]]
    ]
    rejected = await client.post(route, json=body, headers=bearer(token))
    assert rejected.status_code == 422


async def test_exact_watch_refuses_report_template_that_would_lose_its_scope(client, user):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post(
        "/api/warning/indicators",
        headers=bearer(token),
        json={
            "name": "Exact watch",
            "report_template": "osint",
            "research_area": {"geometry": triangle().geometry.to_collection()},
        },
    )
    assert response.status_code == 422
    assert "alerts only" in response.text
