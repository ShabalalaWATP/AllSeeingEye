"""Synthetic OpenAQ records and deterministic, network-free request timing."""

import httpx

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research.openaq_area import OpenAqAreaResearchProvider
from hazard_area_helpers import ACQUIRED_TEXT
from research_feed_helpers import CLOCK

KEY = "synthetic-openaq-test-key"


def location(key=1, lon=2, lat=2, **changes):
    return {
        "id": key,
        "name": f"Station {key}",
        "isMobile": False,
        "coordinates": {"longitude": lon, "latitude": lat},
        "datetimeLast": {"utc": ACQUIRED_TEXT},
        "provider": {"id": 70, "name": "Monitoring provider"},
        "owner": {"id": 4, "name": "Monitoring owner"},
        "licenses": [
            {
                "id": 10,
                "name": "ODC-BY",
                "dateFrom": "2020-01-01",
                "dateTo": None,
                "attribution": {"name": "Station owner", "url": "https://owner.example"},
            }
        ],
        "sensors": [
            {
                "id": key * 100,
                "parameter": {
                    "id": 2,
                    "name": "pm25",
                    "units": "µg/m³",
                    "displayName": "PM2.5",
                },
            }
        ],
        **changes,
    }


def reading(key=1, lon=2, lat=2, **changes):
    return {
        "locationsId": key,
        "sensorsId": key * 100,
        "value": 12.3,
        "coordinates": {"longitude": lon, "latitude": lat},
        "datetime": {"utc": ACQUIRED_TEXT, "local": ACQUIRED_TEXT},
        **changes,
    }


def licence(key=10, **changes):
    return {
        "id": key,
        "name": "ODC-BY",
        "sourceUrl": "https://opendatacommons.org/licenses/by/1.0/",
        "commercialUseAllowed": True,
        "modificationAllowed": True,
        "redistributionAllowed": True,
        "attributionRequired": True,
        "shareAlikeRequired": False,
        **changes,
    }


class OpenAqFeed:
    def __init__(
        self, monkeypatch, locations=None, observations=None, licences=None, response=None
    ):
        self.time = 0.0
        self.requests = []
        self.guarded = []
        self.sleeps = []
        self.locations = locations if locations is not None else [location()]
        self.observations = observations if observations is not None else {1: [reading()]}
        self.licences = licences if licences is not None else {10: licence()}
        self.response = response

        async def guard(url):
            self.guarded.append(url)

        def respond(request):
            self.requests.append(request)
            if self.response is not None:
                return self.response(request)
            if request.url.path == "/v3/locations":
                return httpx.Response(
                    200, json={"meta": {"found": len(self.locations)}, "results": self.locations}
                )
            if request.url.path.endswith("/latest"):
                return httpx.Response(
                    200,
                    json={
                        "results": self.observations.get(int(request.url.path.split("/")[-2]), [])
                    },
                )
            return httpx.Response(
                200, json={"results": [self.licences[int(request.url.path.split("/")[-1])]]}
            )

        monkeypatch.setattr(feed_http, "assert_public_host", guard)
        self.http = FeedHttpClient(
            "tests", client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
        )

    async def sleep(self, delay):
        self.sleeps.append(delay)
        self.time += delay

    def provider(self, key=KEY):
        provider = OpenAqAreaResearchProvider(self.http, CLOCK, key)
        provider._client._timer = lambda: self.time
        provider._client._sleep = self.sleep
        return provider
