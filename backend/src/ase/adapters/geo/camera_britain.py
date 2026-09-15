"""Traffic Scotland's public camera index with same-origin frames, and curated UK catalogues.

Traffic Scotland lists its cameras with positions at one fixed JSON endpoint and serves each
image only as a base64 fragment inside a small HTML snippet. The server relays one decoded
JPEG per request through `/api/cameras/frames/traffic-scotland/<sid>.jpg`, for sids present
in the last index only, with a short cache and a concurrency bound. Nothing else is proxied.
Durham County Council publishes its camera positions as open data and embeds the images from
a contractor host without a key. `uk-live` holds curated YouTube embeds and `uk-local` a
curated set of council, Isle of Man and crossing cameras whose image or HLS URLs are fixed.
"""

import asyncio
import base64
import binascii
import json
import re
import time
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.geo.camera_curated import HostPolicy, collect, curated_rows, valid_position
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera

INDEX = "https://www.traffic.gov.scot/tsis/cameras"
FRAME = "https://www.traffic.gov.scot/tsis/camerahtml?sid="
PAGE = "https://www.traffic.gov.scot/traffic-cameras"
MEDIA_HOSTS = frozenset(
    {
        "dcc.ussgroup.co.uk",
        "images.gov.im",
        "files.argyll-bute.gov.uk",
        "www.cne-siar.gov.uk",
        "www.tamarcrossings.org.uk",
        "stream1.mgw-is.uk",
        "stream2.mgw-is.uk",
        "camsecure.co",
    }
)
FRAME_HOSTS = frozenset({"www.youtube.com"})
EXTERNAL_HOSTS = (
    MEDIA_HOSTS
    | FRAME_HOSTS
    | {"www.traffic.gov.scot", "www.durham.gov.uk", "www.argyll-bute.gov.uk"}
)
NAMES = {
    "traffic-scotland": "Traffic Scotland",
    "durham": "Durham County Council",
    "uk-live": "UK public streams",
    "uk-local": "UK council, island and crossing cameras",
}
PAGES = {"durham": "https://www.durham.gov.uk/trafficcameras"}
CURATED = ("durham", "uk-live", "uk-local")
POLICY = HostPolicy(MEDIA_HOSTS, FRAME_HOSTS, EXTERNAL_HOSTS, NAMES, PAGES)
SCOTLAND_BOUNDS = (54.5, 61.0, -8.7, 0.0)
SID = re.compile(r"[0-9]{1,6}")
JPEG_B64 = re.compile(rb"data:image/jpeg;base64,([A-Za-z0-9+/=]{64,})")
FRAME_TTL_SECONDS = 45.0
FRAME_MAX_BYTES = 2 * 1024 * 1024
FRAME_CACHE_SIZE = 512
INDEX_RETRY_SECONDS = 60.0


def frame_path(sid: str) -> str:
    return f"/api/cameras/frames/traffic-scotland/{sid}.jpg"


def parse_scotland(payload: bytes) -> tuple[Camera, ...]:
    """The index lists sid, title, position, road and region; images come from the frame relay."""
    data = json.loads(payload)
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        raise ValueError("Invalid Traffic Scotland camera index")
    cameras: dict[str, Camera] = {}
    for item in results[:5000]:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("sid") or "")
        position = valid_position(item)
        if SID.fullmatch(sid) is None or position is None:
            continue
        south, north, west, east = SCOTLAND_BOUNDS
        if not (south <= position[0] <= north and west <= position[1] <= east):
            continue
        title = str(item.get("title") or f"Camera {sid}")[:200]
        region = str(item.get("region") or "").strip()[:80]
        cameras[sid] = Camera(
            id=f"traffic-scotland:{sid}",
            provider="traffic-scotland",
            title=f"{title} ({region})" if region else title,
            latitude=position[0],
            longitude=position[1],
            snapshot_url=frame_path(sid),
            source_url=PAGE,
            attribution="Source: Traffic Scotland (Transport Scotland). Provider terms apply. "
            "Frames are relayed by this server from the operator's public camera page.",
            external_url=PAGE,
        )
    if not cameras:
        raise ValueError("Traffic Scotland index held no supported cameras")
    return tuple(cameras.values())


def extract_frame(payload: bytes) -> bytes | None:
    """The first inline JPEG of the camera snippet, decoded and bounded; nothing else is kept."""
    match = JPEG_B64.search(payload)
    if match is None:
        return None
    try:
        data = base64.b64decode(match.group(1), validate=True)
    except (binascii.Error, ValueError):
        return None
    if not data.startswith(b"\xff\xd8\xff") or len(data) > FRAME_MAX_BYTES:
        return None
    return data


class TrafficScotlandSource:
    """Index and frame relay; frames are only served for sids the last index listed."""

    id = "traffic-scotland"
    name = NAMES["traffic-scotland"]

    def __init__(self, http: FeedHttpClient, clock: Callable[[], float] = time.monotonic) -> None:
        self._http = http
        self._clock = clock
        self._known: frozenset[str] = frozenset()
        self._frames: OrderedDict[str, tuple[float, bytes]] = OrderedDict()
        self._limit = asyncio.Semaphore(2)
        self._index_lock = asyncio.Lock()
        self._index_failed_at: float | None = None

    async def fetch(self) -> tuple[Camera, ...]:
        payload = await self._http.get_bytes(INDEX, conditional=False, max_redirects=0)
        cameras = parse_scotland(payload)
        self._known = frozenset(camera.id.split(":", 1)[1] for camera in cameras)
        self._index_failed_at = None
        return cameras

    async def _load_index_for_frames(self) -> None:
        """One shared index load for concurrent frame requests, then a cooldown after failure."""
        async with self._index_lock:
            if self._known:
                return
            failed_at = self._index_failed_at
            if failed_at is not None and self._clock() - failed_at < INDEX_RETRY_SECONDS:
                raise ValueError("Traffic Scotland camera index is temporarily unavailable")
            try:
                await self.fetch()
            except Exception:
                self._index_failed_at = self._clock()
                raise

    async def frame(self, frame_id: str) -> bytes | None:
        if SID.fullmatch(frame_id) is None:
            return None
        if not self._known:
            await self._load_index_for_frames()
        if frame_id not in self._known:
            return None
        now = self._clock()
        cached = self._frames.get(frame_id)
        if cached is not None and now - cached[0] < FRAME_TTL_SECONDS:
            return cached[1]
        async with self._limit:
            payload = await self._http.get_bytes(
                FRAME + frame_id, conditional=False, max_redirects=0
            )
        frame = extract_frame(payload)
        if frame is None:
            raise ValueError("Traffic Scotland returned no image for this camera")
        self._frames[frame_id] = (now, frame)
        self._frames.move_to_end(frame_id)
        while len(self._frames) > FRAME_CACHE_SIZE:
            self._frames.popitem(last=False)
        return frame


class CuratedBritainSource:
    def __init__(self, provider: str, cameras: tuple[Camera, ...]) -> None:
        self.id = provider
        self.name = NAMES[provider]
        self._cameras = cameras

    async def fetch(self) -> tuple[Camera, ...]:
        return self._cameras


def load_catalogue() -> list[dict[str, Any]]:
    path = Path(__file__).with_name("camera_britain_catalogue.json")
    records = json.loads(path.read_text("utf8"))
    if not isinstance(records, list):
        raise ValueError("Invalid British camera catalogue")
    return records


def curated(provider: str, records: list[dict[str, Any]] | None = None) -> tuple[Camera, ...]:
    """Durham positions are the council's own open data; streams are approximate localities."""
    rows = curated_rows(records if records is not None else load_catalogue(), provider)
    return collect(POLICY, provider, rows, approximate=provider != "durham")


def build_sources(http: FeedHttpClient) -> tuple[CameraSource, ...]:
    records = load_catalogue()
    sources: list[CameraSource] = [TrafficScotlandSource(http)]
    sources.extend(CuratedBritainSource(name, curated(name, records)) for name in CURATED)
    return tuple(sources)
