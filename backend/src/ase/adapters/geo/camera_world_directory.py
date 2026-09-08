"""Bounded OpenCCTV Asian directory queries, adapted from OSIRIS (MIT).

The directory is not an authorisation signal for arbitrary upstream cameras.
Unreviewed hosts remain directory links; only approved public hosts embed.
"""

import asyncio
import json
import math
from dataclasses import replace
from time import monotonic
from typing import Any

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.geo.camera_http import CameraHttpClient
from ase.adapters.geo.camera_world import make_camera
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera

MARKERS = "https://opencctv.org/api/cameras/markers"
BATCH = "https://opencctv.org/api/cameras/batch"
BATCH_BUDGET_SECONDS = 28.0
REGIONS = {
    "eastasia": ((18, 46, 73.5, 146), 1200),
    "seasia": ((-11, 24, 92, 130), 800),
    "westasia": ((5, 56, 25, 92), 600),
}
NAMES = {
    "eastasia": "OpenCCTV East Asia",
    "seasia": "OpenCCTV Southeast Asia",
    "westasia": "OpenCCTV West and Central Asia",
}


def regional_ids(index: Any, region: str) -> list[str]:
    if not isinstance(index, dict) or not all(
        isinstance(index.get(key), list) for key in ("ids", "lats", "lngs")
    ):
        raise ValueError("Invalid OpenCCTV marker index")
    bounds, cap = REGIONS[region]
    selected = []
    for key, lat, lon in zip(index["ids"][:200000], index["lats"], index["lngs"], strict=False):
        if not isinstance(key, str) or not key or len(key) > 100:
            continue
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        if (
            math.isfinite(lat)
            and math.isfinite(lon)
            and bounds[0] < lat < bounds[1]
            and bounds[2] < lon < bounds[3]
        ):
            selected.append(key)
    selected = list(dict.fromkeys(selected))
    if len(selected) > cap:
        selected = [selected[i * len(selected) // cap] for i in range(cap)]
    return selected


def map_record(region: str, item: Any) -> Camera | None:
    if not isinstance(item, dict) or item.get("active") == 0:
        return None
    # A directory listing does not prove permission to access its camera host.
    # Keep the listing accessible even when direct media has not been approved.
    row = {**item, "external_url": "https://opencctv.org/", "approximate": True}
    kind = str(item.get("feed_type") or "").lower()
    row["feed_url"] = item.get("feed_url") if kind == "image" else None
    row["stream_url"] = item.get("feed_url") if kind == "iframe" else None
    camera = make_camera("japan", row)
    if camera is None:
        return None
    return replace(
        camera,
        id=f"opencctv:{item['id']}",
        provider=region,
        source_url="https://opencctv.org/",
        attribution="OpenCCTV directory. Upstream operator and playback unverified; "
        "only approved public hosts can display media here.",
    )


class MarkerIndexCache:
    """One bounded index per registry, shared across the three regional loaders."""

    def __init__(self, http: CameraHttpClient) -> None:
        self._http = http
        self._index: dict[str, Any] | None = None
        self._until = 0.0
        self._lock = asyncio.Lock()

    async def get(self) -> dict[str, Any]:
        async with self._lock:
            if self._index is not None and monotonic() < self._until:
                return self._index
            async with asyncio.timeout(12):
                payload = await self._http.get_bytes(MARKERS, conditional=False, max_redirects=0)
            index = json.loads(payload)
            regional_ids(index, "eastasia")  # Validate before caching.
            self._index = {key: index[key][:200000] for key in ("ids", "lats", "lngs")}
            self._until = monotonic() + 900
            return self._index


class DirectorySource:
    def __init__(
        self, region: str, http: CameraHttpClient, index: MarkerIndexCache | None = None
    ) -> None:
        self.id = region
        self.name = NAMES[region]
        self._http = http
        self._index = index or MarkerIndexCache(http)
        self.warning: str | None = None

    async def fetch(self) -> tuple[Camera, ...]:
        self.warning = None
        ids = regional_ids(await self._index.get(), self.id)
        chunks = [ids[i : i + 50] for i in range(0, len(ids), 50)]
        results: dict[str, Camera] = {}
        next_batch = 0
        completed = 0
        failed = 0

        async def worker() -> None:
            nonlocal next_batch, completed, failed
            while next_batch < len(chunks):
                keys = chunks[next_batch]
                next_batch += 1
                try:
                    async with asyncio.timeout(5):
                        data = await self._http.post_json(BATCH, {"ids": keys})
                    if not isinstance(data, list):
                        raise ValueError("Invalid OpenCCTV camera batch")
                    allowed = set(keys)
                    for row in data[:50]:
                        if (
                            isinstance(row, dict)
                            and isinstance(row.get("id"), str)
                            and row["id"] in allowed
                        ):
                            camera = map_record(self.id, row)
                            if camera is not None:
                                results[camera.id] = camera
                    completed += 1
                except (FeedFetchError, OSError, ValueError, TimeoutError):
                    failed += 1

        # Index fetch plus batch work stays below the service's 45-second deadline.
        # Successful batches survive a slow or broken neighbour; cancellation from
        # the caller still propagates and cancels every worker.
        try:
            async with asyncio.timeout(BATCH_BUDGET_SECONDS):
                await asyncio.gather(*(worker() for _ in range(min(4, len(chunks)))))
        except TimeoutError:
            failed += 1
        if failed or completed < len(chunks):
            self.warning = f"Partial directory catalogue: {completed}/{len(chunks)} batches loaded."
            if not results:
                raise ValueError("OpenCCTV camera batch unavailable")
        return tuple(results.values())


def build_sources(http: CameraHttpClient) -> tuple[CameraSource, ...]:
    index = MarkerIndexCache(http)
    return tuple(DirectorySource(region, http, index) for region in REGIONS)
