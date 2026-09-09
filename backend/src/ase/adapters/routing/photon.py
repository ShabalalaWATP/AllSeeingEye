"""Photon public place search, bounded results and no address-bearing diagnostics."""

import json
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.secret_urls import SecretFeedUrl
from ase.domain.events import Point
from ase.domain.navigation import NavigationPlace

ORIGIN = "https://photon.komoot.io"
MAX_BYTES = 128 * 1024


def parse_places(payload: bytes) -> tuple[NavigationPlace, ...]:
    if len(payload) > MAX_BYTES:
        raise ValueError("Place response exceeds limit")
    features = json.loads(payload)["features"]
    if not isinstance(features, list) or len(features) > 5:
        raise ValueError("Invalid place results")
    results = []
    for feature in features:
        geometry, properties = feature["geometry"], feature["properties"]
        coordinates = geometry["coordinates"]
        if geometry["type"] != "Point" or len(coordinates) != 2:
            raise ValueError("Invalid place geometry")
        if any(type(value) not in (int, float) for value in coordinates):
            raise ValueError("Invalid place coordinates")
        point = Point(*coordinates)
        parts = []
        for key in ("name", "housenumber", "street", "postcode", "city", "state", "country"):
            value = properties.get(key)
            if value is not None:
                if not isinstance(value, str) or len(value) > 200:
                    raise ValueError("Invalid place label")
                if value.strip() and value.strip() not in parts:
                    parts.append(value.strip())
        label = ", ".join(parts)
        if not label or len(label) > 1000:
            raise ValueError("Invalid place label")
        results.append(NavigationPlace(label, point))
    return tuple(results)


class PhotonPlaceSearchGateway:
    def __init__(self, http: FeedHttpClient) -> None:
        self._http = http

    async def search(self, query: str) -> tuple[NavigationPlace, ...]:
        target = SecretFeedUrl(
            ORIGIN, f"{ORIGIN}/api/?{urlencode({'q': query, 'limit': 5, 'lang': 'en'})}"
        )
        return parse_places(await self._http.get_secret_bytes(target))
