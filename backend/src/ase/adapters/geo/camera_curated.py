"""Shared validation for catalogue rows. Data can never widen the approved media origins."""

import math
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from ase.domain.cameras import Camera

STREAM_KINDS = frozenset({"hls", "mp4", "mjpeg", "iframe"})
EMBED_PATH = re.compile(r"/embed/[A-Za-z0-9_-]{11}")
MAX_ROWS = 5000


@dataclass(frozen=True)
class HostPolicy:
    """Exact HTTPS origins a module allows, with display names and operator pages."""

    media: frozenset[str]
    frames: frozenset[str]
    external: frozenset[str]
    names: dict[str, str]
    pages: dict[str, str]


def exact_https(value: Any, hosts: frozenset[str]) -> str | None:
    """An HTTPS URL on one listed host; credentials, ports, fragments and controls fail."""
    if not isinstance(value, str) or not value or len(value) > 2048:
        return None
    if any(ord(char) < 33 or ord(char) > 126 for char in value):
        return None
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    if parts.scheme != "https" or parts.netloc not in hosts or parts.fragment:
        return None
    return value


def valid_position(row: dict[str, Any]) -> tuple[float, float] | None:
    try:
        lat, lon = float(row.get("lat", "nan")), float(row.get("lng", "nan"))
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return None
    return lat, lon


def build_camera(
    policy: HostPolicy, provider: str, row: dict[str, Any], *, approximate: bool
) -> Camera | None:
    """Validate even curated records; a row without an approved media or page link is dropped."""
    position = valid_position(row)
    key = str(row.get("id") or "")
    if position is None or not key or len(key) > 160:
        return None
    image = exact_https(row.get("feed_url"), policy.media)
    kind = row.get("stream_type")
    stream = None
    if kind in STREAM_KINDS:
        stream = exact_https(
            row.get("stream_url"), policy.frames if kind == "iframe" else policy.media
        )
    if (
        stream
        and kind == "iframe"
        and urlsplit(stream).netloc == "www.youtube.com"
        and EMBED_PATH.fullmatch(urlsplit(stream).path) is None
    ):
        stream = None
    external = exact_https(row.get("external_url"), policy.external)
    if not (image or stream or external):
        return None
    source = external or policy.pages.get(provider) or stream or image
    attribution = f"Source: {row.get('source') or policy.names.get(provider, provider)}. "
    attribution += "Provider terms apply."
    if approximate:
        attribution += " Approximate position; playback and availability not verified."
    return Camera(
        id=f"{provider}:{key}",
        provider=provider,
        title=str(row.get("name") or policy.names.get(provider, provider))[:240],
        latitude=position[0],
        longitude=position[1],
        snapshot_url=image,
        source_url=str(source),
        attribution=attribution[:1000],
        stream_url=stream,
        stream_type=kind if stream and kind in STREAM_KINDS else None,
        external_url=external or stream,
        coordinate_precision="approximate" if approximate else "exact",
    )


def collect(
    policy: HostPolicy, provider: str, rows: list[dict[str, Any]], *, approximate: bool
) -> tuple[Camera, ...]:
    """Bounded, de-duplicated by id, in catalogue order."""
    cameras = (
        build_camera(policy, provider, row, approximate=approximate) for row in rows[:MAX_ROWS]
    )
    return tuple({camera.id: camera for camera in cameras if camera is not None}.values())


def curated_rows(records: list[dict[str, Any]], provider: str) -> list[dict[str, Any]]:
    return [row for row in records if isinstance(row, dict) and row.get("provider") == provider]
