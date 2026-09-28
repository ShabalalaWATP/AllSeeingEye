"""The attributed OSIRIS country camera catalogues packaged under ``ase.resources``.

Each ``resources/cameras/<country>.json`` holds the records generated from OSIRIS
fac8d1b, unchanged; the MIT notice and attribution are in ``resources/cameras/NOTICE.md``.
Only the fixed country names below can be read. Every record is checked for shape here,
and ``camera_europe.make_camera`` still validates coordinates and media origins.
"""

from __future__ import annotations

from typing import Any, Final, NotRequired, TypedDict, cast

from ase.adapters.packaged_json import (
    CatalogueError,
    fields,
    https_url,
    load_resource,
    number,
    records,
    text,
    unique,
)

COUNTRIES: Final = (
    "bulgaria",
    "serbia",
    "macedonia",
    "romania",
    "italy",
    "czechia",
    "slovakia",
    "germany",
    "france",
    "spain",
    "poland",
    "switzerland",
)
MAX_ROWS: Final = 5000
STREAM_TYPES: Final = frozenset({"hls", "mp4", "mjpeg", "iframe"})
_TEXT: Final = ("id", "name", "city", "country", "source")
_URLS: Final = ("feed_url", "stream_url", "external_url")


class CuratedCameraRow(TypedDict):
    """One upstream record, keys and order as packaged; make_camera reads only some."""

    id: str
    lat: float
    lng: float
    name: str
    city: str
    country: str
    source: str
    feed_url: NotRequired[str]
    stream_url: NotRequired[str]
    stream_type: NotRequired[str]
    external_url: NotRequired[str]


def curated_rows(country: str) -> tuple[CuratedCameraRow, ...]:
    """Read one fixed country file; any other name is refused before a path is built."""
    if country not in COUNTRIES:
        raise ValueError("Unknown curated camera provider")
    return parse_rows(country, load_resource("cameras", f"{country}.json"))


def parse_rows(country: str, data: object) -> tuple[CuratedCameraRow, ...]:
    where = f"cameras/{country}.json"
    rows = tuple(
        _row(f"{where}[{index}]", item) for index, item in enumerate(records(where, data, MAX_ROWS))
    )
    unique(where, [row["id"] for row in rows])
    return rows


def _row(where: str, item: object) -> CuratedCameraRow:
    row: dict[str, Any] = fields(where, item, (*_TEXT, "lat", "lng"), (*_URLS, "stream_type"))
    for key in _TEXT:
        text(f"{where}.{key}", row[key], limit=240)
    for key in ("lat", "lng"):
        number(f"{where}.{key}", row[key])
    for key in _URLS:
        if key in row:
            https_url(f"{where}.{key}", row[key])
    if ("stream_url" in row) != ("stream_type" in row):
        raise CatalogueError(f"{where}: stream_url and stream_type must be given together")
    if row.get("stream_type", "hls") not in STREAM_TYPES:
        raise CatalogueError(f"{where}.stream_type: expected one of {sorted(STREAM_TYPES)}")
    # Every key and value type has been checked above, so the record is the reviewed shape.
    return cast(CuratedCameraRow, row)
