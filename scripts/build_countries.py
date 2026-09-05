"""Builds the packaged country polygons from Natural Earth (public domain).

Downloads the 1:110m admin-0 countries GeoJSON, keeps the ISO codes, name and
geometry, rounds coordinates to three decimals (about 100 m) and writes a compact
JSON resource for the country resolver. Re-run when Natural Earth changes:

    python scripts/build_countries.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_110m_admin_0_countries.geojson"
)
OUTPUT = Path(__file__).resolve().parent.parent / "backend/src/ase/resources/countries_110m.json"
# Natural Earth leaves ISO_A2 as -99 where sovereignty is disputed or split; these are
# the codes the rest of the world uses for them.
FALLBACK_ISO2 = {"FRA": "FR", "NOR": "NO", "KOS": "XK", "SOL": "XS", "CYN": "XN", "SDS": "SS"}
FALLBACK_ISO3 = {"KOS": "XKX", "SOL": "XSL", "CYN": "XNC"}
PRECISION = 3


def ring_points(ring: list[list[float]]) -> list[list[float]]:
    points: list[list[float]] = []
    for lon, lat in ring:
        point = [round(lon, PRECISION), round(lat, PRECISION)]
        if not points or points[-1] != point:
            points.append(point)
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    return points


def polygons(geometry: dict) -> list[list[list[list[float]]]]:
    kind = geometry["type"]
    raw = [geometry["coordinates"]] if kind == "Polygon" else geometry["coordinates"]
    result = []
    for polygon in raw:
        rings = [ring_points(ring) for ring in polygon]
        rings = [ring for ring in rings if len(ring) >= 3]
        if rings:
            result.append(rings)
    return result


def iso_codes(props: dict) -> tuple[str, str] | None:
    adm0 = str(props.get("ADM0_A3") or "")
    iso2 = str(props.get("ISO_A2_EH") or props.get("ISO_A2") or "")
    iso3 = str(props.get("ISO_A3_EH") or props.get("ISO_A3") or "")
    if len(iso2) != 2 or not iso2.isalpha():
        iso2 = FALLBACK_ISO2.get(adm0, "")
    if len(iso3) != 3 or not iso3.isalpha():
        iso3 = FALLBACK_ISO3.get(adm0, adm0 if len(adm0) == 3 else "")
    if not iso2 or not iso3:
        return None
    return iso2.upper(), iso3.upper()


def main() -> int:
    with urllib.request.urlopen(URL, timeout=120) as response:  # noqa: S310 (fixed https URL)
        data = json.load(response)
    countries = []
    skipped = []
    for feature in data["features"]:
        props = feature["properties"]
        codes = iso_codes(props)
        if codes is None:
            skipped.append(props.get("NAME"))
            continue
        countries.append(
            {
                "iso2": codes[0],
                "iso3": codes[1],
                "name": props.get("NAME_EN") or props.get("NAME") or codes[0],
                "polygons": polygons(feature["geometry"]),
            }
        )
    countries.sort(key=lambda item: item["iso2"])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"source": URL, "licence": "Public domain", "countries": countries}, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB, {len(countries)} countries)")
    if skipped:
        print("skipped without ISO codes:", ", ".join(map(str, skipped)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
