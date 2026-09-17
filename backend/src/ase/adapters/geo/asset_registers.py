"""Scan the packaged infrastructure registers for one resolved scope. No network, no cost.

Every dataset here is already shipped with the application and already drawn on the map.
This module only counts and names what a register holds inside a scope, with that
register's own attribution and snapshot date. It asserts nothing about current state.
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from ase.adapters.geo.infrastructure import public_infrastructure
from ase.adapters.geo.scope_geography import ResolvedScope
from ase.domain.area_assets import AssetClass
from ase.domain.area_inventory import (
    MAX_LISTED_ITEMS,
    MAX_RECORDS_SCANNED,
    RegisterEntry,
    RegisterItem,
    bound_entries,
)
from ase.domain.evidence import injection_flags

BY_OUTLINE = "exact position inside the resolved outline"
BY_COUNTRY = "the dataset's own declared country field"
BY_PATH = "exact intersection of the mapped route with the resolved outline"

# Dataset key, human name, and the metadata keys carrying attribution and snapshot date.
_DATASETS: dict[AssetClass, tuple[str, str, str, str, str | None]] = {
    AssetClass.DATA_CENTRES: (
        "data_centres",
        "Data centres",
        "data_centre_attribution",
        "data_centre_snapshot_date",
        "data_centre_licence_url",
    ),
    AssetClass.ENERGY_SITES: (
        "energy_sites",
        "Energy sites",
        "site_attribution",
        "site_snapshot_date",
        "site_licence_url",
    ),
    AssetClass.SEMICONDUCTOR_SITES: (
        "semiconductor_sites",
        "Semiconductor sites",
        "site_attribution",
        "site_snapshot_date",
        "site_licence_url",
    ),
    AssetClass.NUCLEAR_FACILITIES: (
        "nuclear_facilities",
        "Nuclear facilities",
        "nuclear_attribution",
        "nuclear_snapshot_date",
        "nuclear_licence_url",
    ),
    AssetClass.GROUND_STATIONS: (
        "ground_stations",
        "Satellite ground stations",
        "ground_station_attribution",
        "snapshot_date",
        None,
    ),
    AssetClass.SUBMARINE_CABLES: (
        "cables",
        "Submarine cable segments",
        "cable_attribution",
        "snapshot_date",
        "cable_licence_url",
    ),
}
GROUND_STATION_ATTRIBUTION = (
    "Curated list resolved through Wikidata; no dataset licence is recorded."
)


def _text(value: Any, limit: int) -> str:
    return str(value)[:limit] if isinstance(value, str | int | float) else ""


def _number(value: Any) -> float | None:
    return float(value) if type(value) in (int, float) and math.isfinite(value) else None


def _https(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith("https://") and len(value) <= 500:
        return value
    return None


def _country_label(row: Mapping[str, Any]) -> str | None:
    value = _text(row.get("country"), 60)
    return value or None


def _item(row: Mapping[str, Any]) -> RegisterItem | None:
    name = _text(row.get("name"), 200).strip()
    note = _text(row.get("significance") or row.get("note") or row.get("description"), 600)
    if not name or injection_flags(name, note):
        return None
    return RegisterItem(
        name,
        _country_label(row),
        _text(row.get("precision"), 60) or "not recorded",
        _https(row.get("source_url")) or _https(row.get("website")) or _https(row.get("wikipedia")),
    )


def _rows(snapshot: Mapping[str, Any], key: str) -> Sequence[Mapping[str, Any]]:
    value = snapshot.get(key)
    return value if isinstance(value, list) else ()


def _point_matches(
    rows: Sequence[Mapping[str, Any]],
    scope: ResolvedScope,
    isos: frozenset[str],
) -> Iterator[Mapping[str, Any]]:
    for row in rows[:MAX_RECORDS_SCANNED]:
        if not isinstance(row, Mapping):
            continue
        if isos:
            declared = _text(row.get("country"), 8).upper()
            code = _text(row.get("country_code"), 8).upper()
            if declared in isos or (len(code) == 3 and code in isos):
                yield row
            continue
        lon, lat = _number(row.get("longitude")), _number(row.get("latitude"))
        if lon is not None and lat is not None and scope.contains_point(lon, lat):
            yield row


def _path_matches(
    rows: Sequence[Mapping[str, Any]], scope: ResolvedScope
) -> Iterator[Mapping[str, Any]]:
    for row in rows[:MAX_RECORDS_SCANNED]:
        path = row.get("path") if isinstance(row, Mapping) else None
        if isinstance(path, list) and scope.crosses_path(path):
            yield row


def _entry(
    asset: AssetClass,
    snapshot: Mapping[str, Any],
    matched: Sequence[Mapping[str, Any]],
    matched_by: str,
    truncated: bool,
) -> RegisterEntry:
    key, name, attribution_key, as_of_key, licence_key = _DATASETS[asset]
    listed = []
    for row in sorted(matched, key=lambda row: _text(row.get("name"), 200)):
        item = _item(row)
        if item is not None:
            listed.append(item)
        if len(listed) == MAX_LISTED_ITEMS:
            break
    attribution = _text(snapshot.get(attribution_key), 500) or (
        GROUND_STATION_ATTRIBUTION if asset is AssetClass.GROUND_STATIONS else "not recorded"
    )
    return RegisterEntry(
        asset.value,
        f"map:{key}",
        name,
        len(matched),
        tuple(listed),
        _text(snapshot.get(as_of_key), 40) or "not recorded",
        attribution,
        matched_by,
        _https(snapshot.get(licence_key)) if licence_key else None,
        truncated,
    )


def scan_registers(
    classes: frozenset[AssetClass],
    scope: ResolvedScope,
    *,
    country_isos: tuple[str, ...] = (),
    snapshot: Mapping[str, Any] | None = None,
) -> tuple[RegisterEntry, ...]:
    """Counts and up to six named records per eligible class, in register order.

    Country scopes match point datasets on the dataset's declared country field, which is
    what those datasets actually assert. Cable routes carry no country, so they are always
    matched by exact intersection with the resolved outline.
    """
    data = snapshot if snapshot is not None else public_infrastructure()
    isos = frozenset(value.upper() for value in country_isos)
    entries = []
    for asset in AssetClass:
        if asset not in classes or asset not in _DATASETS:
            continue
        rows = _rows(data, _DATASETS[asset][0])
        truncated = len(rows) > MAX_RECORDS_SCANNED
        if asset is AssetClass.SUBMARINE_CABLES:
            matched, matched_by = list(_path_matches(rows, scope)), BY_PATH
        else:
            matched = list(_point_matches(rows, scope, isos))
            matched_by = BY_COUNTRY if isos else BY_OUTLINE
        entries.append(_entry(asset, data, matched, matched_by, truncated))
    return bound_entries(tuple(entries))
