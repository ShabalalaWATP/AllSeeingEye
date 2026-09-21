"""Describe every registered camera provider from its adapter class and the cached status.

The camera service's snapshot reads only cached metadata, so this never refreshes a
provider or fetches imagery. Delivery follows the adapter class: official indexes are
fetched from the publisher, curated catalogues ship with the application, and OpenCCTV is
a third-party directory.
"""

from __future__ import annotations

from dataclasses import dataclass

from ase.adapters.geo import (
    camera_americas,
    camera_americas_cars,
    camera_americas_ibi,
    camera_britain,
    camera_britain_councils,
    camera_east,
    camera_europe,
    camera_europe_maps,
    camera_europe_open,
    camera_world,
    camera_world_directory,
    camera_world_open,
    camera_wsdot,
    cameras,
)
from ase.application.cameras import CameraCatalogueService
from ase.application.source_assets import AssetDelivery, SourceAsset, delivery_detail
from ase.application.source_inventory import ConnectionState, SourceRequirement
from ase.container.camera_coverage import CAMERA_COVERAGE
from ase.domain.cameras import CameraProviderStatus
from ase.domain.users import User

WSDOT_SETTING = "ASE_WSDOT_ACCESS_CODE"
OPENCCTV_HOME = "https://opencctv.org/"


@dataclass(frozen=True, slots=True)
class _Family:
    delivery: AssetDelivery
    document: str


_AMERICAS = _Family("official_index", "docs/CAMERA_AMERICAS.md")
_EUROPE = _Family("official_index", "docs/CAMERA_EUROPE.md")
_UK = _Family("official_index", "docs/CAMERA_EUROPE.md")
_CURATED_EUROPE = _Family("curated_catalogue", "docs/CAMERA_EUROPE.md")
_CURATED_REGION = _Family("curated_catalogue", "docs/CAMERA_WORLD.md")
_FAMILIES: tuple[tuple[type, _Family], ...] = (
    (cameras.OfficialCameraSource, _Family("official_index", "docs/CAMERA_FEEDS.md")),
    (
        camera_wsdot.WsdotCameraSource,
        _Family("official_index", _AMERICAS.document),
    ),
    (camera_americas.AmericanCameraSource, _AMERICAS),
    (camera_americas_ibi.IbiCameraSource, _AMERICAS),
    (camera_americas_cars.CarsCameraSource, _AMERICAS),
    (
        camera_americas.AmericanPublishedLinks,
        _Family("curated_catalogue", _AMERICAS.document),
    ),
    (camera_europe_open.OpenEuropeSource, _EUROPE),
    (camera_europe_maps.EuropeMapSource, _EUROPE),
    (camera_britain.TrafficScotlandSource, _UK),
    (
        camera_britain.CuratedBritainSource,
        _Family("curated_catalogue", _UK.document),
    ),
    (
        camera_britain_councils.CouncilCameraSource,
        _UK,
    ),
    (camera_east.EstoniaCameraSource, _EUROPE),
    (camera_east.CuratedEastSource, _CURATED_EUROPE),
    (
        camera_world.WorldCameraSource,
        _Family("official_index", _CURATED_REGION.document),
    ),
    (camera_world.CuratedWorldSource, _CURATED_REGION),
    (
        camera_world_directory.DirectorySource,
        _Family("third_party_directory", _CURATED_REGION.document),
    ),
    (
        camera_world_open.WorldOpenSource,
        _Family("official_index", _CURATED_REGION.document),
    ),
)


def _family(source: object) -> _Family:
    if isinstance(source, camera_europe.EuropeanCameraSource):
        return _EUROPE if source.id in camera_europe.ENDPOINTS else _CURATED_EUROPE
    for kind, family in _FAMILIES:
        if isinstance(source, kind):
            return family
    return _Family("official_index", "docs/CAMERA_FEEDS.md")


def _homepage(source: object, provider: str) -> str | None:
    config = getattr(source, "cfg", None)
    base = getattr(config, "base", None)
    if isinstance(base, str):
        return base
    if isinstance(source, camera_world_directory.DirectorySource):
        return OPENCCTV_HOME
    if isinstance(source, camera_wsdot.WsdotCameraSource):
        return camera_wsdot.SOURCE_URL
    if isinstance(source, camera_britain.TrafficScotlandSource):
        return camera_britain.PAGE
    for pages in (
        cameras.SOURCES,
        camera_britain.PAGES,
        camera_britain_councils.PAGES,
        camera_east.PAGES,
        camera_europe_open.PAGES,
        camera_europe_maps.PAGES,
        camera_world_open.PAGES,
    ):
        if provider in pages:
            return pages[provider]
    return None


def _licence(delivery: AssetDelivery, provider: str, document: str) -> str:
    if provider in cameras.ATTRIBUTION:
        return cameras.ATTRIBUTION[provider]
    if delivery == "curated_catalogue":
        return (
            "Curated public records adapted from OSIRIS (MIT); positions are approximate and "
            f"playback is not verified. Camera owners' terms apply. See {document}."
        )
    if delivery == "third_party_directory":
        return (
            "OpenCCTV aggregates third-party records; only reviewed HTTPS hosts display media. "
            f"Camera owners' terms apply. See {document}."
        )
    return f"Publisher terms apply; each camera carries its attribution. See {document}."


def _state(
    delivery: AssetDelivery, status: CameraProviderStatus | None
) -> tuple[ConnectionState, str, int | None]:
    if delivery == "curated_catalogue":
        count = status.count if status and status.status == "available" else None
        return ConnectionState.AVAILABLE, delivery_detail(delivery), count
    if status is None or status.status == "not_loaded":
        return ConnectionState.ON_DEMAND, delivery_detail(delivery), None
    if status.status == "available":
        return ConnectionState.CONNECTED, "Serving cameras from the latest refresh.", status.count
    if status.status == "stale":
        return (
            ConnectionState.DEGRADED,
            "The latest refresh failed; serving cameras from an earlier refresh.",
            status.count,
        )
    return (
        ConnectionState.DEGRADED,
        "The latest refresh failed; it is retried when the map next asks.",
        None,
    )


def camera_assets(
    service: CameraCatalogueService, user: User, wsdot_code: bool
) -> list[SourceAsset]:
    statuses = {row.id: row for row in service.snapshot(user, limit=1).providers}
    assets = []
    for source in service.sources:
        inner = getattr(source, "source", source)
        family = _family(inner)
        state, detail, records = _state(family.delivery, statuses.get(source.id))
        requirement = None
        if isinstance(inner, camera_wsdot.WsdotCameraSource):
            requirement = SourceRequirement(
                "api_key",
                wsdot_code,
                "environment" if wsdot_code else "none",
                WSDOT_SETTING,
                "A WSDOT access code is configured on the server."
                if wsdot_code
                else f"Set {WSDOT_SETTING} on the server to load Washington State cameras.",
            )
            if not wsdot_code:
                state, detail = ConnectionState.KEY_MISSING, requirement.note
        assets.append(
            SourceAsset(
                id=f"camera:{source.id}",
                name=source.name,
                family="camera_index",
                delivery=family.delivery,
                organisation=source.name,
                description="Public camera provider in the CCTV layer.",
                licence_note=_licence(family.delivery, source.id, family.document),
                homepage=_homepage(inner, source.id),
                coverage_note=CAMERA_COVERAGE.get(source.id, "Coverage not specified."),
                refresh_note="Cached for 15 minutes after the map requests this provider."
                if family.delivery != "curated_catalogue"
                else "Updated with the application.",
                state=state,
                detail=detail,
                requirement=requirement,
                records=records,
            )
        )
    return assets
