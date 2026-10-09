"""Source dependencies of map displays and packaged map records."""

from ase.domain.source_licences import SourceLicencePolicy

INFRASTRUCTURE_SOURCES = {
    "cables": "map:submarine_cables",
    "ground_stations": "map:ground_stations",
    "nuclear_facilities": "map:nuclear_facilities",
    "data_centres": "map:data_centres",
    "energy_sites": "map:energy_sites",
    "semiconductor_sites": "map:semiconductor_sites",
}
MAP_SOURCE_IDS = (
    *INFRASTRUCTURE_SOURCES.values(),
    "map:military_source_index",
    "map:natural_earth_countries",
    "map:openfreemap",
    "map:eox_s2cloudless",
    "map:os_maps",
    "map:nasa_gibs_daily",
    "map:terrain_elevation",
    "map:photon_places",
    "map:valhalla_routing",
    "reference:entities",
    "reference:public_figures",
    "reference:conflicts",
    "ukraine:viina_control",
    "ukraine:oblast_outlines",
    "ukraine:oryx_losses",
    "ukraine:hrmmu_casualties",
    "ukraine:reference_catalogue",
    "ukraine:deepstate",
    "ukraine:ocha_frontline",
    "ukraine:warspotting",
)


def require_basemap(licences: SourceLicencePolicy, basemap: str) -> None:
    """Every raster uses OpenFreeMap beneath it, including saved image exports."""
    licences.require("map:openfreemap")
    if basemap in {"satellite", "hybrid"}:
        licences.require("map:eox_s2cloudless")
    elif basemap.startswith("os_"):
        licences.require("map:os_maps")
