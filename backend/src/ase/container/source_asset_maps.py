"""Map layers, described from their packaged metadata.

Attribution, licence and snapshot dates come from the resource files through the same
cached loaders the map and reference endpoints use. Browser-direct base maps and
request-time services name their public provider only; nothing here contacts them.
"""

from __future__ import annotations

from typing import Any

from ase.adapters.geo.countries import load_records
from ase.adapters.geo.infrastructure import public_infrastructure
from ase.adapters.routing import photon, valhalla
from ase.application.source_assets import (
    AssetDelivery,
    AssetFamily,
    SourceAsset,
    delivery_detail,
    snapshot_state,
)
from ase.application.source_inventory import ConnectionState

OSM_HOME = "https://www.openstreetmap.org/"
OSM_LICENCE = "OpenStreetMap data (ODbL); the provider's attribution is shown on the map."
SNAPSHOT: AssetDelivery = "bundled_snapshot"
TERRAIN_ATTRIBUTION = "https://github.com/tilezen/joerd/blob/master/docs/attribution.md"


def asset(
    key: str,
    name: str,
    family: AssetFamily,
    delivery: AssetDelivery,
    organisation: str,
    description: str,
    licence: str,
    homepage: str | None,
    coverage: str,
    refresh: str,
    *,
    command: str | None = None,
    present: bool = True,
    as_of: str | None = None,
    records: int | None = None,
) -> SourceAsset:
    if delivery == "bundled_snapshot":
        state, detail = snapshot_state(present, command or "the documented import")
    else:
        state, detail = ConnectionState.ON_DEMAND, delivery_detail(delivery)
    return SourceAsset(
        id=key,
        name=name,
        family=family,
        delivery=delivery,
        organisation=organisation,
        description=description,
        licence_note=licence,
        homepage=homepage,
        coverage_note=coverage,
        refresh_note=refresh,
        state=state,
        detail=detail,
        as_of=as_of,
        records=records if present else None,
    )


def _items(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    return len(value) if isinstance(value, list) else 0


def map_layer_assets() -> list[SourceAsset]:
    data = public_infrastructure()
    nuclear_home = (data.get("_provenance") or {}).get("source_url")
    return [
        asset(
            "map:data_centres",
            "Data centres",
            "map_layer",
            SNAPSHOT,
            "OpenStreetMap contributors",
            "Named data centre features on the infrastructure layer.",
            str(data["data_centre_attribution"]),
            OSM_HOME,
            "Worldwide; incomplete and uneven between countries.",
            "Refresh with ase import-data-centres.",
            command="ase import-data-centres",
            as_of=str(data["data_centre_snapshot_date"]),
            records=_items(data, "data_centres"),
        ),
        asset(
            "map:energy_sites",
            "Energy sites",
            "map_layer",
            SNAPSHOT,
            "Wikidata and OpenStreetMap contributors",
            "Power stations, refineries, terminals and other energy infrastructure.",
            str(data["site_attribution"]),
            OSM_HOME,
            "Worldwide; incomplete and uneven between countries.",
            "Refresh with ase import-energy-sites.",
            command="ase import-energy-sites",
            as_of=str(data["site_snapshot_date"]),
            records=_items(data, "energy_sites"),
        ),
        asset(
            "map:semiconductor_sites",
            "Semiconductor sites",
            "map_layer",
            SNAPSHOT,
            "Wikidata and OpenStreetMap contributors",
            "Fabrication, packaging and design sites of strategic chip companies.",
            str(data["site_attribution"]),
            OSM_HOME,
            "Worldwide; curated key sites plus mapped breadth.",
            "Refresh with ase import-semiconductor-sites.",
            command="ase import-semiconductor-sites",
            records=_items(data, "semiconductor_sites"),
        ),
        asset(
            "map:submarine_cables",
            "Submarine cables",
            "map_layer",
            SNAPSHOT,
            "OpenStreetMap contributors",
            "Approximate mapped submarine cable segments for connectivity context.",
            str(data["cable_attribution"]),
            OSM_HOME,
            "Worldwide; approximate and incomplete.",
            "Packaged snapshot; ase import-infrastructure-notes adds descriptive fields.",
            as_of=str(data["snapshot_date"]),
            records=_items(data, "cables"),
        ),
        asset(
            "map:nuclear_facilities",
            "Nuclear facilities",
            "map_layer",
            SNAPSHOT,
            "World Resources Institute",
            "Nuclear subset of the Global Power Plant Database; historical records.",
            str(data["nuclear_attribution"]),
            nuclear_home if isinstance(nuclear_home, str) else None,
            "Worldwide; historical, not current operating status.",
            "Packaged snapshot; ase import-infrastructure-notes adds descriptive fields.",
            as_of=str(data["nuclear_snapshot_date"]),
            records=_items(data, "nuclear_facilities"),
        ),
        asset(
            "map:ground_stations",
            "Satellite ground stations",
            "map_layer",
            SNAPSHOT,
            "Curated list resolved through Wikidata",
            "Satellite ground stations and teleports with their operators.",
            "No dataset licence is recorded; each station links its public source page.",
            "https://www.wikidata.org/",
            "Worldwide; curated, not complete.",
            "Refresh with ase import-ground-stations.",
            command="ase import-ground-stations",
            records=_items(data, "ground_stations"),
        ),
        asset(
            "map:military_source_index",
            "Military infrastructure source register",
            "map_layer",
            SNAPSHOT,
            "Official government and alliance publications",
            "Country-level register of official public documents about military "
            "infrastructure. Source metadata only, with no site coordinates.",
            "Titles, dates and links to official publications; publishers' terms apply.",
            None,
            "Selected countries; coverage is not complete.",
            "Packaged with the web application and reviewed by hand.",
        ),
        asset(
            "map:natural_earth_countries",
            "Country outlines",
            "map_layer",
            SNAPSHOT,
            "Natural Earth",
            "1:110m country boundaries used for country lookup and outlines.",
            "Public domain.",
            "https://www.naturalearthdata.com/",
            "Worldwide at small scale.",
            "Updated with the application.",
            records=len(load_records()),
        ),
        asset(
            "map:openfreemap",
            "OpenFreeMap vector base maps",
            "map_layer",
            "browser_direct",
            "OpenFreeMap",
            "Dark, streets and light vector base map styles.",
            OSM_LICENCE,
            "https://openfreemap.org/",
            "Worldwide.",
            "Tiles are requested by the browser as you pan and zoom.",
        ),
        asset(
            "map:eox_s2cloudless",
            "Sentinel-2 cloudless imagery",
            "map_layer",
            "browser_direct",
            "EOX IT Services",
            "Annual cloud-free satellite mosaic used as the satellite base map.",
            "Sentinel-2 cloudless 2024 by EOX IT Services (CC BY-NC-SA 4.0), contains "
            "modified Copernicus Sentinel data 2024.",
            "https://s2maps.eu/",
            "Worldwide.",
            "Tiles are requested by the browser as you pan and zoom.",
        ),
        asset(
            "map:terrain_elevation",
            "Terrain elevation tiles",
            "map_layer",
            "request_service",
            "Mapzen Terrain Tiles (AWS Open Data)",
            "Elevation samples for line-of-sight, radio and route profiles.",
            "Multi-source terrain data; the full attribution travels with each response.",
            TERRAIN_ATTRIBUTION,
            "Worldwide within Web Mercator latitude limits.",
            "Decoded tiles are cached in memory; nothing is stored.",
        ),
        asset(
            "map:photon_places",
            "Photon place search",
            "map_layer",
            "request_service",
            "Komoot Photon",
            "Place name search for navigation.",
            OSM_LICENCE,
            photon.ORIGIN,
            "Worldwide.",
            "Queried per search; nothing is stored.",
        ),
        asset(
            "map:valhalla_routing",
            "Valhalla routing",
            "map_layer",
            "request_service",
            "FOSSGIS",
            "Road and foot routes for the route planner.",
            OSM_LICENCE,
            valhalla.ORIGIN,
            "Worldwide.",
            "Queried per route; nothing is stored.",
        ),
    ]
