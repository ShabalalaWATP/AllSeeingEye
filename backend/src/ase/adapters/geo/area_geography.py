"""Assemble everything the packaged geometry alone can say about one report's scope.

Only geometry already shipped with the application is read: the drawn outline, the
Natural Earth 1:110m country outlines, the geoBoundaries Ukraine oblast outlines and
the curated camera catalogues. Nothing is fetched, nothing is geocoded, and a point
that is not precisely located is never placed anywhere.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from shapely.geometry import Point as ShapePoint
from shapely.geometry import Polygon
from shapely.prepared import prep

from ase.adapters.geo.asset_registers import BY_OUTLINE, scan_registers
from ase.adapters.geo.countries import load_records
from ase.adapters.geo.scope_geography import (
    ResolvedScope,
    from_area,
    from_conflict_box,
    from_countries,
)
from ase.application.ports.area_geography import EvidencePlacement, ScopeSample
from ase.domain.area_assets import AssetClass
from ase.domain.area_context import (
    MAX_BREAKDOWN_ROWS,
    AreaBreakdown,
    AreaGeographyResult,
    BreakdownRow,
    ContainmentSplit,
    ScopeReceipt,
)
from ase.domain.area_inventory import MAX_LISTED_ITEMS, RegisterEntry, RegisterItem
from ase.domain.research_area import ResearchArea

EXACT = "exact"
PLACE_LEVEL = frozenset({"city", "admin1"})
COUNTRY_LEVEL = "country"
MAX_CAMERAS_SCANNED = 5_000

OBLAST_ATTRIBUTION = "geoBoundaries ADM1 (ODbL), OpenStreetMap contributors."
COUNTRY_ATTRIBUTION = "Natural Earth 1:110m country outlines (public domain)."
CAMERA_ATTRIBUTION = (
    "Curated public camera catalogues packaged with the application. Metadata only: no "
    "image, stream or current availability was checked."
)
_CAMERA_FILES = (
    "camera_britain_catalogue.json",
    "camera_east_catalogue.json",
    "camera_world_catalogue.json",
)


@lru_cache(maxsize=1)
def _oblasts() -> tuple[tuple[str, Polygon], ...]:
    raw = json.loads(
        files("ase.resources").joinpath("ukraine_oblasts.json").read_text(encoding="utf-8")
    )
    result: list[tuple[str, Polygon]] = []
    for outline in raw.get("outlines", []):
        name = str(outline.get("name") or outline.get("iso") or "")[:120]
        for rings in outline.get("polygons", []):
            if name and rings and len(rings[0]) >= 4:
                polygon = Polygon(rings[0], rings[1:])
                if polygon.is_valid and not polygon.is_empty:
                    result.append((name, polygon))
    return tuple(result)


@lru_cache(maxsize=1)
def _cameras() -> tuple[tuple[str, str, float, float], ...]:
    """Provider, name and position for each packaged curated camera, bounded."""
    rows: list[tuple[str, str, float, float]] = []
    for name in _CAMERA_FILES:
        path = Path(__file__).with_name(name)
        for row in json.loads(path.read_text("utf8"))[:MAX_CAMERAS_SCANNED]:
            lon, lat = row.get("lng"), row.get("lat")
            label = str(row.get("name") or "")[:200]
            if label and type(lon) in (int, float) and type(lat) in (int, float):
                rows.append((str(row.get("provider") or "unknown")[:60], label, lon, lat))
    return tuple(rows)


def _classify(scope: ResolvedScope, placements: Sequence[EvidencePlacement]) -> ContainmentSplit:
    inside = outside = place = country = unlocated = 0
    for row in placements:
        located = row.lon is not None and row.lat is not None
        if row.geo_confidence == EXACT and located:
            if scope.contains_point(float(row.lon or 0.0), float(row.lat or 0.0)):
                inside += 1
            else:
                outside += 1
        elif row.geo_confidence in PLACE_LEVEL and located:
            place += 1
        elif row.geo_confidence == COUNTRY_LEVEL:
            country += 1
        else:
            unlocated += 1
    return ContainmentSplit(inside, outside, place, country, unlocated)


def _tally(
    named: Sequence[tuple[str, Polygon]],
    scope: ResolvedScope,
    placements: Sequence[EvidencePlacement],
) -> tuple[dict[str, int], int]:
    prepared = [(name, prep(polygon)) for name, polygon in named]
    counts: dict[str, int] = {}
    unassigned = 0
    for row in placements:
        if row.geo_confidence != EXACT or row.lon is None or row.lat is None:
            continue
        if not scope.contains_point(float(row.lon), float(row.lat)):
            continue
        point = ShapePoint(float(row.lon), float(row.lat))
        match = next((name for name, shape_ in prepared if shape_.covers(point)), None)
        if match is None:
            unassigned += 1
        else:
            counts[match] = counts.get(match, 0) + 1
    return counts, unassigned


def _breakdown(
    dataset: str,
    attribution: str,
    named: Sequence[tuple[str, Polygon]],
    scope: ResolvedScope,
    placements: Sequence[EvidencePlacement],
) -> AreaBreakdown | None:
    counts, unassigned = _tally(named, scope, placements)
    if not counts:
        return None
    ordered = sorted(counts.items(), key=lambda row: (-row[1], row[0]))[:MAX_BREAKDOWN_ROWS]
    return AreaBreakdown(
        dataset,
        attribution,
        tuple(BreakdownRow(name, count) for name, count in ordered),
        unassigned,
    )


def _country_polygons() -> tuple[tuple[str, Polygon], ...]:
    result: list[tuple[str, Polygon]] = []
    for record in load_records():
        name = str(record.get("name") or record["iso2"])[:120]
        for rings in record.get("polygons", []):
            if rings and len(rings[0]) >= 4:
                polygon = Polygon(rings[0], rings[1:])
                if polygon.is_valid and not polygon.is_empty:
                    result.append((name, polygon))
    return tuple(result)


def _camera_entry(scope: ResolvedScope) -> RegisterEntry | None:
    matched = [row for row in _cameras() if scope.contains_point(row[2], row[3])]
    if not matched:
        return None
    listed = tuple(
        RegisterItem(label, provider, "catalogue position", None)
        for provider, label, _, _ in sorted(matched, key=lambda row: row[1])[:MAX_LISTED_ITEMS]
    )
    return RegisterEntry(
        AssetClass.CAMERAS.value,
        "map:curated_cameras",
        "Curated public cameras",
        len(matched),
        listed,
        "packaged with the application",
        CAMERA_ATTRIBUTION,
        BY_OUTLINE,
    )


def _scope_for(
    area: ResearchArea | None,
    country_isos: tuple[str, ...],
    box: tuple[float, float, float, float] | None,
    box_label: str | None,
) -> ResolvedScope | None:
    if area is not None:
        return from_area(area)
    if country_isos:
        resolved = from_countries(country_isos)
        if resolved is not None:
            return resolved
    if box is not None and box_label:
        return from_conflict_box(box_label, box_label, box)
    return None


class PackagedAreaGeography:
    """The only geography service: packaged outlines, exact tests and no invention."""

    def assemble(
        self,
        *,
        area: ResearchArea | None,
        country_isos: tuple[str, ...],
        box: tuple[float, float, float, float] | None = None,
        box_label: str | None = None,
        placements: Sequence[EvidencePlacement] = (),
        cameras: bool = False,
    ) -> AreaGeographyResult | None:
        try:
            scope = _scope_for(area, country_isos, box, box_label)
        except ValueError:
            return None
        if scope is None:
            return None
        receipt = ScopeReceipt(scope.scope.basis, scope.scope.label, scope.scope.limitation)
        containment = _classify(scope, placements)
        breakdown = tuple(
            row
            for row in (
                _breakdown(
                    "geoBoundaries Ukraine oblasts",
                    OBLAST_ATTRIBUTION,
                    _oblasts(),
                    scope,
                    placements,
                ),
                _breakdown(
                    "Natural Earth countries",
                    COUNTRY_ATTRIBUTION,
                    _country_polygons(),
                    scope,
                    placements,
                ),
            )
            if row is not None
        )
        coverage = _camera_entry(scope) if cameras else None
        registers = (coverage,) if coverage is not None else ()
        return AreaGeographyResult(receipt, containment, breakdown, registers)

    def locate(
        self,
        *,
        area: ResearchArea | None,
        country_isos: tuple[str, ...],
        box: tuple[float, float, float, float] | None = None,
        box_label: str | None = None,
        samples: Sequence[ScopeSample] = (),
    ) -> frozenset[str]:
        """The same resolved scope as assemble, asked only whether a point is inside it."""
        try:
            scope = _scope_for(area, country_isos, box, box_label)
        except ValueError:
            return frozenset()
        if scope is None:
            return frozenset()
        return frozenset(row.key for row in samples if scope.contains_point(row.lon, row.lat))

    def register_entries(
        self, *, area: ResearchArea | None, country_isos: tuple[str, ...], classes: Sequence[str]
    ) -> tuple[RegisterEntry, ...]:
        """Kept for callers that need the register scan without the containment work."""
        scope = _scope_for(area, country_isos, None, None)
        if scope is None:
            return ()
        wanted = frozenset(AssetClass(value) for value in classes if value in set(AssetClass))
        isos = () if area is not None else country_isos
        return scan_registers(wanted, scope, country_isos=isos)


def geography_snapshot() -> dict[str, Any]:
    """Row counts of the packaged geometry, for inventories and diagnostics."""
    return {"oblasts": len(_oblasts()), "cameras": len(_cameras())}
