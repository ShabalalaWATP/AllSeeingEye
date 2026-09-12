"""One source-2, multi-country, multi-indicator request with twelve annual periods."""

import math
from dataclasses import replace
from datetime import date, datetime
from typing import Any
from urllib.parse import urlencode

from ase.domain.economy import EconomyPoint, EconomyRegion
from ase.domain.economy_catalogue import (
    ANNUAL_PERIODS,
    INDICATORS,
    REGIONS,
    annual_note,
    empty_regions,
)

MAX_ROWS = len(REGIONS) * len(INDICATORS) * ANNUAL_PERIODS


def world_bank_url(now: datetime) -> str:
    countries = ";".join(code for _, _, code in REGIONS)
    indicators = ";".join(code for _, _, code, _ in INDICATORS)
    query = urlencode(
        {
            "source": 2,
            "format": "json",
            "date": f"{now.year - ANNUAL_PERIODS}:{now.year - 1}",
            "per_page": MAX_ROWS,
            "page": 1,
        }
    )
    return f"https://api.worldbank.org/v2/country/{countries}/indicator/{indicators}?{query}"


def parse_world_bank(data: Any, now: datetime) -> tuple[EconomyRegion, ...]:
    if not isinstance(data, list) or len(data) != 2 or not isinstance(data[0], dict):
        raise ValueError("Invalid economic indicators response")
    metadata, rows = data
    if metadata.get("pages") != 1 or metadata.get("page") != 1:
        raise ValueError("Incomplete economic indicators response")
    if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS:
        raise ValueError("Invalid economic indicator rows")
    updated = metadata.get("lastupdated")
    try:
        updated = date.fromisoformat(updated).isoformat() if isinstance(updated, str) else None
    except ValueError:
        updated = None
    values = _observations(rows, now)
    result = []
    for region in empty_regions():
        series = []
        for item in region.series:
            points = tuple(
                EconomyPoint(str(year), values.get((region.id, item.id, str(year))))
                for year in range(now.year - ANNUAL_PERIODS, now.year)
            )
            available = any(point.value is not None for point in points)
            series.append(
                replace(
                    item,
                    points=points,
                    status="available" if available else "unavailable",
                    updated_at=now,
                    source_updated_at=updated,
                    note=annual_note(item.id)
                    + (" No non-missing observations were supplied." if not available else ""),
                )
            )
        result.append(replace(region, series=tuple(series)))
    return tuple(result)


def _observations(rows: list[Any], now: datetime) -> dict[tuple[str, str, str], float | None]:
    countries = {code: region for region, _, code in REGIONS}
    indicators = {code: key for key, _, code, _ in INDICATORS}
    values: dict[tuple[str, str, str], float | None] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("indicator"), dict):
            continue
        country, indicator = row.get("countryiso3code"), row["indicator"].get("id")
        if not isinstance(country, str) or not isinstance(indicator, str):
            continue
        if country not in countries or indicator not in indicators:
            continue
        year = row.get("date")
        if not isinstance(year, str) or len(year) != 4 or not year.isascii() or not year.isdigit():
            continue
        if not now.year - ANNUAL_PERIODS <= int(year) < now.year:
            continue
        value = row.get("value")
        if value is not None and (
            type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e20
        ):
            continue
        key = (countries[country], indicators[indicator], year)
        numeric = float(value) if value is not None else None
        if key in values and values[key] != numeric:
            raise ValueError("Contradictory economic observations")
        values[key] = numeric
    if not values:
        raise ValueError("No recognised economic observations")
    return values
