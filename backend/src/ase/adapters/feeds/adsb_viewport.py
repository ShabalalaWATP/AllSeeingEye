"""Bounded, short-lived map interests for authenticated viewport-driven collection."""

import math
from collections import OrderedDict
from datetime import datetime, timedelta

from ase.adapters.feeds.adsb import adsb_spec
from ase.adapters.feeds.adsb_classification import AircraftClassificationCache
from ase.adapters.feeds.adsb_watch import AdsbAreaConnector, WatchArea
from ase.adapters.feeds.http import FeedHttpClient
from ase.application.ports import Clock
from ase.domain.events import Event

MAX_INTERESTS = 32
INTEREST_TTL = timedelta(minutes=5)
SPEC = adsb_spec(
    "adsb_viewport",
    "Aircraft in requested map areas (adsb.lol)",
    "https://api.adsb.lol/v2/point",
    seconds=30,
)


class AircraftInterestQueue:
    """Shared by one feed worker. Call request only after authenticating a map request."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._items: OrderedDict[tuple[int, int], datetime] = OrderedDict()

    def request(self, latitude: float, longitude: float) -> None:
        if not (
            math.isfinite(latitude)
            and math.isfinite(longitude)
            and -90 <= latitude <= 90
            and -180 <= longitude <= 180
        ):
            raise ValueError("Invalid aircraft map interest")
        key = (round(latitude), round(longitude))
        self._items[key] = self._clock.now() + INTEREST_TTL
        self._items.move_to_end(key)
        while len(self._items) > MAX_INTERESTS:
            self._items.popitem(last=False)

    def take(self) -> tuple[WatchArea, ...]:
        now = self._clock.now()
        for key, expiry in tuple(self._items.items()):
            if expiry <= now:
                del self._items[key]
        selected = list(self._items)[:4]
        for key in selected:
            self._items.move_to_end(key)
        return tuple(
            WatchArea(f"viewport_{lat}_{lon}", "Requested map area", lat, lon, 250)
            for lat, lon in selected
        )


class AdsbViewportConnector(AdsbAreaConnector):
    spec = SPEC

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        interests: AircraftInterestQueue,
        *,
        classifications: AircraftClassificationCache | None = None,
    ) -> None:
        super().__init__(
            http,
            clock,
            (),
            classifications=classifications,
            max_areas_per_poll=4,
            request_interval=1.0,
        )
        self._interests = interests

    async def fetch(self) -> list[Event]:
        self._areas = self._interests.take()
        self._start_area = 0
        return await super().fetch()
