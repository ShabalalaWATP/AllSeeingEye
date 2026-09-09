"""Validate a bounded WRI historical nuclear power-plant snapshot offline."""

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

MAX_FACILITIES = 1_000
NOTE = (
    "Historical nuclear power-plant location from WRI. Approximate coordinates; "
    "current operation, ownership and capacity are not verified. "
    "Not a complete inventory of research, enrichment, waste or military facilities."
)


def nuclear_facilities(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Normalise the licensed subset without inferring live plant status."""
    if len(rows) > MAX_FACILITIES:
        raise ValueError("Nuclear snapshot exceeds the facility limit")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("primary_fuel") != "Nuclear":
            continue
        identifier = row.get("gppd_idnr")
        country_code = row.get("country")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", identifier):
            continue
        if not isinstance(country_code, str) or not re.fullmatch(r"[A-Z]{3}", country_code):
            continue
        try:
            latitude, longitude = float(row["latitude"]), float(row["longitude"])
        except (KeyError, ValueError, TypeError):
            continue
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            continue
        name = _text(row.get("name"))
        if not name:
            continue
        year = _text(row.get("year_of_capacity_data"))
        result.setdefault(
            identifier,
            {
                "id": f"wri-nuclear-{identifier}",
                "name": name,
                "country": _text(row.get("country_long")) or country_code,
                "country_code": country_code,
                "latitude": latitude,
                "longitude": longitude,
                "capacity_mw": _capacity(row.get("capacity_mw")),
                "capacity_year": int(year) if re.fullmatch(r"(?:19|20)[0-9]{2}", year) else None,
                "operator": _text(row.get("owner")) or None,
                "source_name": _text(row.get("source")) or "World Resources Institute",
                "source_url": _url(row.get("url")),
                "geolocation_source": _text(row.get("geolocation_source")) or "WRI",
                "note": NOTE,
            },
        )
    return sorted(result.values(), key=lambda item: (item["country"], item["name"], item["id"]))


def _text(value: object) -> str:
    return value.strip()[:300] if isinstance(value, str) else ""


def _capacity(value: object) -> float | None:
    try:
        number = float(str(value))
    except ValueError:
        return None
    return number if math.isfinite(number) and 0 <= number <= 100_000 else None


def _url(value: object) -> str:
    fallback = "https://github.com/wri/global-power-plant-database"
    if not isinstance(value, str) or len(value) > 2_000 or any(ord(c) < 33 for c in value):
        return fallback
    try:
        parsed = urlsplit(value)
        if parsed.scheme in {"https", "http"} and parsed.hostname and not parsed.username:
            return value
    except ValueError:
        pass
    return fallback
