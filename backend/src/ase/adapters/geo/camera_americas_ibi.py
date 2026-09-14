"""Bounded public IBI 511 catalogue readers. See docs/CAMERA_AMERICAS.md for attribution."""

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urljoin

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.geo.camera_americas_common import camera, unique
from ase.domain.cameras import Camera


@dataclass(frozen=True)
class IbiConfig:
    id: str
    name: str
    base: str
    bounds: tuple[float, float, float, float]


CONFIGS = (
    IbiConfig("utah", "UDOT Traffic", "https://prod-ut.ibi511.com", (36.9, 42.1, -114.2, -108.9)),
    IbiConfig("nevada", "NDOT", "https://www.nvroads.com", (34.9, 42.1, -120.1, -113.9)),
    IbiConfig("louisiana", "LADOTD", "https://511la.org", (28.8, 33.1, -94.2, -88.6)),
    IbiConfig("florida", "FDOT", "https://fl511.com", (24.3, 31.1, -87.7, -79.8)),
    IbiConfig("georgia", "GDOT", "https://511ga.org", (30.3, 35.1, -85.7, -80.8)),
    IbiConfig("northcarolina", "NCDOT", "https://www.drivenc.gov", (33.8, 36.6, -84.4, -75.4)),
    IbiConfig("arizona", "ADOT", "https://az511.gov", (31.3, 37.1, -115.0, -109.0)),
    IbiConfig("newyork", "511NY", "https://511ny.org", (40.4, 45.1, -79.9, -71.7)),
    IbiConfig("pennsylvania", "511PA", "https://www.511pa.com", (39.6, 42.4, -80.6, -74.6)),
    IbiConfig(
        "newengland", "New England 511", "https://newengland511.org", (41.2, 47.5, -73.8, -66.8)
    ),
    IbiConfig("idaho", "Idaho 511", "https://511.idaho.gov", (41.9, 49.1, -117.4, -110.9)),
    IbiConfig("connecticut", "CTroads", "https://ctroads.org", (40.9, 42.1, -73.8, -71.7)),
    IbiConfig("alaska", "Alaska 511", "https://511.alaska.gov", (51.0, 71.6, -180.0, -129.9)),
    IbiConfig(
        "novascotia", "Nova Scotia 511", "https://511.novascotia.ca", (43.3, 47.1, -66.5, -59.6)
    ),
    IbiConfig(
        "newbrunswick", "New Brunswick 511", "https://511.gnb.ca", (44.5, 48.2, -69.1, -63.7)
    ),
    IbiConfig(
        "saskatchewan",
        "Saskatchewan Highway Hotline",
        "https://hotline.gov.sk.ca",
        (48.9, 60.1, -110.1, -101.3),
    ),
    IbiConfig(
        "newfoundland",
        "511 Newfoundland and Labrador",
        "https://511nl.ca",
        (46.5, 60.5, -67.9, -52.5),
    ),
    IbiConfig("yukon", "511 Yukon", "https://511yukon.ca", (59.9, 69.7, -141.1, -123.7)),
    IbiConfig(
        "manitoba", "Manitoba 511", "https://www.manitoba511.ca", (48.9, 60.1, -102.1, -88.9)
    ),
)


def page_url(cfg: IbiConfig, start: int) -> str:
    query = {
        "columns": [
            {"data": None, "name": ""},
            {"name": "sortOrder", "s": True},
            {"name": "roadway", "s": True},
            {"data": 3, "name": ""},
        ],
        "order": [{"column": 1, "dir": "asc"}],
        "start": start,
        "length": 100,
        "search": {"value": ""},
    }
    return cfg.base + "/List/GetData/Cameras?query=" + quote(json.dumps(query)) + "&lang=en"


def parse_record(cfg: IbiConfig, row: Any) -> Camera | None:
    if not isinstance(row, dict) or type(row.get("id")) is not int:
        return None
    images = row.get("images")
    if not isinstance(images, list) or not images or not isinstance(images[0], dict):
        return None
    image = images[0]
    if image.get("blocked") or image.get("disabled"):
        return None
    location = row.get("latLng") or {}
    if not isinstance(location, dict):
        return None
    geo = location.get("geography") or {}
    geo = geo if isinstance(geo, dict) else {}
    match = re.fullmatch(
        r"POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)",
        str(geo.get("wellKnownText", "")),
        re.I,
    )
    if not match:
        return None
    labels = (
        [image.get("description"), row.get("location"), row.get("roadway")]
        if cfg.id == "nevada"
        else [row.get("location"), row.get("roadway"), image.get("description")]
    )
    title = next(
        (s.strip() for s in labels if isinstance(s, str) and s.strip() not in ("", "N/A")), cfg.name
    )
    video = image.get("videoUrl")
    if (
        image.get("videoDisabled")
        or image.get("isVideoAuthRequired")
        or not isinstance(video, str)
        or not re.search(r"\.m3u8(?:\?|$)", video, re.I)
    ):
        video = None
    snapshot = image.get("imageUrl")
    return camera(
        cfg.id,
        cfg.name,
        cfg.base,
        row["id"],
        title,
        match[2],
        match[1],
        urljoin(cfg.base, snapshot) if isinstance(snapshot, str) else None,
        stream=video,
        bounds=cfg.bounds,
        external=cfg.base,
    )


class IbiCameraSource:
    def __init__(self, cfg: IbiConfig, http: FeedHttpClient) -> None:
        self.id, self.name, self.cfg, self.http = cfg.id, cfg.name, cfg, http

    async def _page(self, start: int) -> tuple[list[Any], int]:
        url = page_url(self.cfg, start)
        try:
            body = await self.http.get_bytes(url, conditional=False, max_redirects=0)
        except FeedFetchError as exc:
            if not re.search(r"HTTP 5[0-9]{2} ", str(exc)):
                raise
            # Retry a transient server failure once, never an access denial.
            body = await self.http.get_bytes(url, conditional=False, max_redirects=0)
        data = json.loads(body)
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise ValueError("Invalid 511 catalogue")
        total = data.get("recordsTotal")
        if type(total) is not int or total < 0:
            raise ValueError("Invalid 511 catalogue count")
        rows = data["data"]
        if len(rows) < min(100, max(0, min(total, 5000) - start)):
            raise ValueError("Incomplete 511 catalogue page")
        return rows[:100], total

    async def fetch(self) -> tuple[Camera, ...]:
        rows, total = await self._page(0)
        # Four concurrent requests, 50 pages maximum. A failed page fails the refresh.
        for start in range(100, min(total, 5000), 400):
            pages = await asyncio.gather(
                *(self._page(i) for i in range(start, min(start + 400, total, 5000), 100))
            )
            for batch, _ in pages:
                rows.extend(batch)
        return unique([parse_record(self.cfg, row) for row in rows])
