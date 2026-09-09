"""FOSSGIS Valhalla, fixed origin, no retries, redirects or coordinate-bearing logs."""

import json
import math
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.secret_urls import SecretFeedUrl
from ase.domain.events import Point
from ase.domain.navigation import NavigationRoute, RouteMode, RouteStep

ORIGIN = "https://valhalla1.openstreetmap.de"
MAX_BYTES = 2 * 1024 * 1024
MAX_POINTS = 20_000
MAX_STEPS = 500


def _number(value: object, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("Invalid routing number")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= maximum:
        raise ValueError("Invalid routing number")
    return result


def _shape(value: object) -> tuple[Point, ...]:
    """Decode the documented polyline6 response, bounding every varint and coordinate."""
    if not isinstance(value, str) or not 2 <= len(value) <= 200_000:
        raise ValueError("Invalid routing shape")
    position = 0
    lat = lon = 0
    points = []
    while position < len(value):
        pair = []
        for _ in range(2):
            encoded = shift = 0
            while True:
                if position >= len(value) or shift > 30:
                    raise ValueError("Invalid routing shape")
                part = ord(value[position]) - 63
                position += 1
                if not 0 <= part <= 63:
                    raise ValueError("Invalid routing shape")
                encoded |= (part & 31) << shift
                shift += 5
                if part < 32:
                    break
            pair.append(~(encoded >> 1) if encoded & 1 else encoded >> 1)
        lat += pair[0]
        lon += pair[1]
        points.append(Point(lon / 1_000_000, lat / 1_000_000))
        if len(points) > MAX_POINTS:
            raise ValueError("Routing shape exceeds limit")
    if len(points) < 2:
        raise ValueError("Empty routing shape")
    return tuple(points)


def parse_route(payload: bytes, mode: RouteMode, waypoint_count: int) -> NavigationRoute:
    if len(payload) > MAX_BYTES:
        raise ValueError("Routing response exceeds limit")
    root = json.loads(payload)
    trip = root["trip"]
    if type(trip["status"]) is not int or trip["status"] != 0 or trip["units"] != "kilometers":
        raise ValueError("No supported route")
    legs = trip["legs"]
    if not isinstance(legs, list) or len(legs) != waypoint_count - 1:
        raise ValueError("Invalid route legs")
    coordinates: list[Point] = []
    steps = []
    for leg in legs:
        coordinates.extend(_shape(leg["shape"]))
        if len(coordinates) > MAX_POINTS:
            raise ValueError("Routing shape exceeds limit")
        manoeuvres = leg["maneuvers"]
        if not isinstance(manoeuvres, list) or not manoeuvres:
            raise ValueError("Invalid directions")
        for item in manoeuvres:
            instruction = item["instruction"]
            if (
                not isinstance(instruction, str)
                or not instruction.strip()
                or len(instruction) > 500
            ):
                raise ValueError("Invalid direction text")
            if any(ord(char) < 32 for char in instruction):
                raise ValueError("Invalid direction text")
            steps.append(
                RouteStep(instruction, _number(item["length"], 5000), _number(item["time"], 604800))
            )
            if len(steps) > MAX_STEPS:
                raise ValueError("Directions exceed limit")
    return NavigationRoute(
        mode,
        _number(trip["summary"]["length"], 5000),
        _number(trip["summary"]["time"], 604800),
        tuple(coordinates),
        tuple(steps),
    )


class ValhallaRoutingGateway:
    def __init__(self, http: FeedHttpClient) -> None:
        self._http = http

    async def route(self, mode: RouteMode, waypoints: tuple[Point, ...]) -> NavigationRoute:
        request = {
            "locations": [
                {"lat": point.lat, "lon": point.lon, "type": "break"} for point in waypoints
            ],
            "costing": {"driving": "auto", "walking": "pedestrian", "cycling": "bicycle"}[mode],
            "units": "kilometers",
            "language": "en-GB",
            "shape_format": "polyline6",
        }
        target = SecretFeedUrl(
            ORIGIN, ORIGIN + "/route?" + urlencode({"json": json.dumps(request)})
        )
        return parse_route(await self._http.get_secret_bytes(target), mode, len(waypoints))
