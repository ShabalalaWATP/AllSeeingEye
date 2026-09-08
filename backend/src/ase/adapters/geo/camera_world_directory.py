"""Bounded OpenCCTV Asian directory queries, adapted from OSIRIS (MIT).

The directory is not an authorisation signal for arbitrary upstream cameras.
Unreviewed hosts remain directory links; only approved public hosts embed.
"""

import asyncio
import json
import math
from dataclasses import replace
from typing import Any

from ase.adapters.geo.camera_http import CameraHttpClient
from ase.adapters.geo.camera_world import make_camera
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera

MARKERS = "https://opencctv.org/api/cameras/markers"
BATCH = "https://opencctv.org/api/cameras/batch"
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


class DirectorySource:
    def __init__(self, region: str, http: CameraHttpClient) -> None:
        self.id = region
        self.name = NAMES[region]
        self._http = http

    async def fetch(self) -> tuple[Camera, ...]:
        payload = await self._http.get_bytes(MARKERS, conditional=False, max_redirects=0)
        ids = regional_ids(json.loads(payload), self.id)
        semaphore = asyncio.Semaphore(4)

        async def batch(keys: list[str]) -> list[Camera]:
            async with semaphore:
                data = await self._http.post_json(BATCH, {"ids": keys})
            if not isinstance(data, list):
                raise ValueError("Invalid OpenCCTV camera batch")
            allowed = set(keys)
            results = (
                map_record(self.id, row)
                for row in data[:50]
                if isinstance(row, dict) and row.get("id") in allowed
            )
            return [camera for camera in results if camera is not None]

        batches = await asyncio.gather(*(batch(ids[i : i + 50]) for i in range(0, len(ids), 50)))
        return tuple({camera.id: camera for cameras in batches for camera in cameras}.values())


def build_sources(http: CameraHttpClient) -> tuple[CameraSource, ...]:
    return tuple(DirectorySource(region, http) for region in REGIONS)
