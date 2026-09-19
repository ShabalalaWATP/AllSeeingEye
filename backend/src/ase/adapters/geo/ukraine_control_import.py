"""VIINA 2.0 territorial control (ODbL) into one bounded snapshot: areas, frontline zone, changes.

The source lists a daily status for every populated place. This importer keeps the latest
day, dissolves Russian-held and contested cells into display areas, retains the settlements
near the reported line, and records recent status changes. Operator-run, never at runtime.
"""

from __future__ import annotations

import csv
import io
import json
import math
import tempfile
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import IO, Any, cast

import httpx
from shapely.geometry import shape
from shapely.ops import unary_union

from ase.adapters.geo.bounded_download import DEFAULT_CONTACT, download_to, user_agent
from ase.adapters.geo.ukraine_geometry import polygon_lists
from ase.domain.ukraine.control import MAX_CHANGES, MAX_SETTLEMENTS, ControlStatus, parse_status

REPOSITORY = "https://github.com/zhukovyuri/VIINA"
CONTROL_URL = (
    "https://media.githubusercontent.com/media/zhukovyuri/VIINA/main/Data/control_latest_{year}.zip"
)
TESSELLATION_URL = "https://raw.githubusercontent.com/zhukovyuri/VIINA/main/Data/gn_UA_tess.geojson"
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
MAX_CSV_BYTES = 768 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 8
MAX_PLACES = 50_000
MAX_CONTROL_ROWS = 15_000_000
MAX_RETAINED_RUNS = MAX_PLACES * 2
ZONE_KM = 25.0
CHANGE_WINDOW_DAYS = 30
TOLERANCE_DEGREES = 0.004
ATTRIBUTION = (
    "Zhukov, Yuri and Natalie Ayers (2023). VIINA 2.0: Violent Incident Information from "
    "News Articles on the 2022 Russian Invasion of Ukraine. Harvard University."
)
METHOD_NOTE = (
    "Status per populated place is the source's majority vote of Wikipedia crowd maps, "
    "those maps boosted by geocoded news reports, DeepStateMap and ISW polygons. It is a "
    "reported line, not observed positions; areas are settlement cells dissolved and simplified."
)


@dataclass(slots=True)
class PlaceHistory:
    runs: list[tuple[str, ControlStatus]] = field(default_factory=list)
    votes: tuple[ControlStatus, ControlStatus, ControlStatus, ControlStatus] = (
        ControlStatus.UNKNOWN,
    ) * 4
    stamp: str = ""


def read_control(handle: io.TextIOBase) -> tuple[dict[int, PlaceHistory], str]:
    """Run-length status history per place; the file is sorted by place then day."""
    reader = csv.reader(handle)
    header = next(reader)
    columns = {name: index for index, name in enumerate(header)}
    needed = (
        "geonameid",
        "date",
        "status_wiki",
        "status_boost",
        "status_dsm",
        "status_isw",
        "status",
    )
    if any(name not in columns for name in needed):
        raise ValueError("Control file is missing expected columns")
    places: dict[int, PlaceHistory] = {}
    latest = ""
    for row_count, row in enumerate(reader, start=1):
        if row_count > MAX_CONTROL_ROWS:
            raise ValueError("Control file contains too many rows")
        place_id = int(float(row[columns["geonameid"]]))
        if place_id not in places and len(places) >= MAX_PLACES:
            raise ValueError("Control file contains too many places")
        place = places.setdefault(place_id, PlaceHistory())
        day = row[columns["date"]]
        status = parse_status(row[columns["status"]])
        if not place.runs:
            place.runs.append((day, status))
        elif place.runs[-1][1] != status:
            # Snapshot generation needs only the current run and its immediate
            # predecessor. Discard older history while streaming so alternating
            # attacker-controlled statuses cannot retain millions of objects.
            place.runs[:] = [place.runs[-1], (day, status)]
        if day >= latest:
            latest = day
            place.votes = tuple(  # type: ignore[assignment]
                parse_status(row[columns[name]])
                for name in ("status_wiki", "status_boost", "status_dsm", "status_isw")
            )
            place.stamp = (
                row[columns.get("vcontrol_version", 0)] if "vcontrol_version" in columns else ""
            )
    if not places or not latest:
        raise ValueError("Control file held no rows")
    if sum(len(place.runs) for place in places.values()) > MAX_RETAINED_RUNS:
        raise ValueError("Control file exceeded its retained history budget")
    return places, latest


def _iso(day: str) -> str:
    return f"{day[:4]}-{day[4:6]}-{day[6:8]}"


def _near(lat: float, lon: float, grid: dict[tuple[int, int], list[tuple[float, float]]]) -> bool:
    cell = (int(lat * 4), int(lon * 4))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for other_lat, other_lon in grid.get((cell[0] + dy, cell[1] + dx), ()):
                dy_km = (lat - other_lat) * 111.0
                dx_km = (lon - other_lon) * 111.0 * math.cos(math.radians(lat))
                if math.hypot(dx_km, dy_km) <= ZONE_KM:
                    return True
    return False


def build_snapshot(
    places: dict[int, PlaceHistory],
    latest: str,
    tessellation: dict[str, Any],
    retrieved_at: datetime,
) -> dict[str, Any]:
    features = {
        int(float(f["properties"]["geonameid"])): f for f in tessellation.get("features", [])
    }
    assessment = date.fromisoformat(_iso(latest))
    cutoff = date.fromordinal(assessment.toordinal() - CHANGE_WINDOW_DAYS).strftime("%Y%m%d")
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    grid: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)
    cells: dict[ControlStatus, list[Any]] = defaultdict(list)
    changes: list[dict[str, Any]] = []
    for place_id, history in places.items():
        feature = features.get(place_id)
        if feature is None:
            continue
        properties, status = feature["properties"], history.runs[-1][1]
        oblast = str(properties.get("ADM1_NAME") or "Unknown oblast")[:80]
        counts[oblast]["total"] += 1
        counts[oblast][status.value] += 1
        lat, lon = float(properties["latitude"]), float(properties["longitude"])
        if status is not ControlStatus.UA:
            grid[(int(lat * 4), int(lon * 4))].append((lat, lon))
        if status in (ControlStatus.RU, ControlStatus.CONTESTED):
            cells[status].append(shape(feature["geometry"]))
        if len(history.runs) > 1 and history.runs[-1][0] >= cutoff:
            changes.append(
                {
                    "geoname_id": place_id,
                    "name": str(properties.get("name") or "")[:80],
                    "oblast": oblast,
                    "previous": history.runs[-2][1].value,
                    "status": status.value,
                    "changed_on": _iso(history.runs[-1][0]),
                }
            )
    settlements: list[list[Any]] = []
    for place_id, history in places.items():
        feature = features.get(place_id)
        if feature is None:
            continue
        properties, status = feature["properties"], history.runs[-1][1]
        lat, lon = float(properties["latitude"]), float(properties["longitude"])
        if status is ControlStatus.UA and not _near(lat, lon, grid):
            continue
        since = _iso(history.runs[-1][0]) if len(history.runs) > 1 else None
        settlements.append(
            [
                place_id,
                str(properties.get("name") or "")[:80],
                str(properties.get("ADM1_NAME") or "Unknown oblast")[:80],
                round(lat, 4),
                round(lon, 4),
                status.value,
                since,
                [vote.value for vote in history.votes],
            ]
        )
    if len(settlements) > MAX_SETTLEMENTS:
        raise ValueError("Frontline zone retains more settlements than the bound allows")
    changes.sort(key=lambda item: (item["changed_on"], item["name"]), reverse=True)
    areas = [
        {
            "status": status.value,
            "polygons": polygon_lists(
                unary_union(cells[status]).simplify(TOLERANCE_DEGREES, preserve_topology=True)
            ),
        }
        for status in (ControlStatus.RU, ControlStatus.CONTESTED)
        if cells[status]
    ]
    stamp = next((h.stamp for h in places.values() if h.stamp), "")
    return {
        "assessment_date": assessment.isoformat(),
        "release_stamp": stamp[:40],
        "retrieved_at": retrieved_at.isoformat(timespec="seconds"),
        "source_url": REPOSITORY,
        "attribution": ATTRIBUTION,
        "licence": "ODbL 1.0",
        "method_note": METHOD_NOTE,
        "places_total": sum(row["total"] for row in counts.values()),
        "settlements": settlements,
        "areas": areas,
        "oblasts": [
            {
                "name": name,
                "total": row["total"],
                "ua": row["ua"],
                "ru": row["ru"],
                "contested": row["contested"],
                "unknown": row["unknown"],
            }
            for name, row in sorted(counts.items())
        ],
        "changes": changes[:MAX_CHANGES],
    }


def _control_from_zip(path: Path) -> tuple[dict[int, PlaceHistory], str]:
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise ValueError("Control archive contains too many members")
        names = [item for item in members if item.filename.endswith(".csv")]
        if len(names) != 1 or names[0].file_size > MAX_CSV_BYTES:
            raise ValueError("Control archive must hold exactly one bounded CSV")
        with archive.open(names[0]) as raw:
            bounded = cast(Any, _BoundedReader(raw, MAX_CSV_BYTES))
            return read_control(io.TextIOWrapper(bounded, encoding="utf-8"))


class _BoundedReader(io.BufferedIOBase):
    """Count actual inflated ZIP bytes because central-directory sizes are untrusted."""

    def __init__(self, source: IO[bytes], maximum: int) -> None:
        self._source = source
        self._maximum = maximum
        self._received = 0

    def readable(self) -> bool:
        return True

    def read(self, size: int | None = -1) -> bytes:
        data = self._source.read(-1 if size is None else size)
        if data:
            self._received += len(data)
            if self._received > self._maximum:
                raise ValueError("Control CSV exceeded its inflated byte limit")
        return data

    def read1(self, size: int = -1) -> bytes:
        return self.read(size)


def import_ukraine_control(
    destination: str, contact: str = DEFAULT_CONTACT, year: int | None = None
) -> int:
    now = datetime.now(UTC)
    url = CONTROL_URL.format(year=year or now.year)
    with (
        httpx.Client(timeout=600, headers={"User-Agent": user_agent(contact)}) as client,
        tempfile.TemporaryDirectory() as folder,
    ):
        archive, tessellation = Path(folder) / "control.zip", Path(folder) / "tess.geojson"
        download_to(client, url, archive, MAX_DOWNLOAD_BYTES)
        download_to(client, TESSELLATION_URL, tessellation, MAX_DOWNLOAD_BYTES)
        places, latest = _control_from_zip(archive)
        snapshot = build_snapshot(
            places, latest, json.loads(tessellation.read_text(encoding="utf-8")), now
        )
    Path(destination).write_text(json.dumps(snapshot, separators=(",", ":")), encoding="utf-8")
    return len(snapshot["settlements"])
