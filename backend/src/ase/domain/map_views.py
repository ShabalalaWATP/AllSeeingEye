"""Immutable saved-map values, independent of renderer, storage and authorisation."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.map_geometry import CanonicalMapGeometry

BASEMAPS = frozenset(
    {"dark", "streets", "light", "satellite", "hybrid", "os_road", "os_outdoor", "os_light"}
)
MAX_VIEW_BYTES = 6 * 1024 * 1024
MAX_SCOPE_VIEWS = 100
MAX_VIEW_REVISIONS = 100
MAX_SCOPE_REVISION_BYTES = 100 * 1024 * 1024


def bounded_text(value: str, maximum: int, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"Invalid map {field}")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"Invalid map {field}")
    value.encode("utf-8")
    return value


def finite(value: float, minimum: float, maximum: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not minimum <= value <= maximum
    ):
        raise ValueError("Invalid map camera value")


@dataclass(frozen=True, slots=True)
class MapCamera:
    longitude: float
    latitude: float
    zoom: float
    bearing: float = 0
    pitch: float = 0

    def __post_init__(self) -> None:
        finite(self.longitude, -180, 180)
        finite(self.latitude, -90, 90)
        finite(self.zoom, 0, 22)
        finite(self.bearing, -180, 180)
        finite(self.pitch, 0, 60)


@dataclass(frozen=True, slots=True)
class MapOverlay:
    geometry: CanonicalMapGeometry
    source: str
    dataset_date: date
    attribution: str
    precision: str
    visible: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.geometry, CanonicalMapGeometry):
            raise ValueError("Map overlay requires canonical geometry")
        bounded_text(self.source, 200, "overlay source")
        bounded_text(self.attribution, 500, "attribution")
        if type(self.dataset_date) is not date:
            raise ValueError("Map overlay requires a dataset date")
        if not isinstance(self.precision, str) or self.precision not in {
            "exact",
            "approximate",
            "unknown",
        }:
            raise ValueError("Invalid map overlay precision")
        if type(self.visible) is not bool:
            raise ValueError("Invalid map overlay visibility")


@dataclass(frozen=True, slots=True)
class MapViewState:
    camera: MapCamera
    projection: str = "globe"
    basemap: str = "dark"
    source_ids: tuple[str, ...] = ()
    published_since: datetime | None = None
    published_until: datetime | None = None
    include_unknown_dates: bool = True
    selected_evidence: str | None = None
    overlays: tuple[MapOverlay, ...] = ()
    aoi: CanonicalMapGeometry | None = None
    schema_version: int = 1
    display_transform: str = "ase-geojson-display-v1"
    time_basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION

    def __post_init__(self) -> None:
        if not isinstance(self.camera, MapCamera):
            raise ValueError("Map state requires an immutable camera")
        if not isinstance(self.time_basis, EvidenceTimeBasis):
            raise ValueError("Unsupported map time basis")
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("Unsupported map state version")
        if (
            not isinstance(self.projection, str)
            or not isinstance(self.basemap, str)
            or self.projection not in {"globe", "mercator"}
            or self.basemap not in BASEMAPS
        ):
            raise ValueError("Unsupported map projection or basemap")
        if self.display_transform not in ("ase-geojson-display-v1", "ase-geojson-display-v2"):
            raise ValueError("Unsupported map display transform")
        if type(self.source_ids) is not tuple or len(self.source_ids) > 64:
            raise ValueError("Map views allow at most 64 source filters")
        for source in self.source_ids:
            bounded_text(source, 128, "source identifier")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("Map source filters must be unique")
        self._validate_dates()
        if type(self.include_unknown_dates) is not bool:
            raise ValueError("Invalid map unknown-date filter")
        if self.selected_evidence is not None:
            bounded_text(self.selected_evidence, 128, "evidence reference")
        self._validate_geometry()

    def _validate_dates(self) -> None:
        for cutoff in (self.published_since, self.published_until):
            if cutoff is not None and (
                not isinstance(cutoff, datetime) or cutoff.utcoffset() is None
            ):
                raise ValueError("Map publication cutoff requires a timezone")
            if cutoff is not None:
                try:
                    cutoff.astimezone(UTC)
                except OverflowError as exc:
                    raise ValueError("Map publication cutoff exceeds the UTC date range") from exc
        if (
            self.published_since is not None
            and self.published_until is not None
            and self.published_since > self.published_until
        ):
            raise ValueError("Map publication interval is reversed")

    def _validate_geometry(self) -> None:
        if type(self.overlays) is not tuple or len(self.overlays) > 8:
            raise ValueError("Map views allow at most eight overlays")
        if any(not isinstance(overlay, MapOverlay) for overlay in self.overlays):
            raise ValueError("Map state requires immutable overlays")
        geometries = [overlay.geometry for overlay in self.overlays]
        if self.aoi is not None:
            if not isinstance(self.aoi, CanonicalMapGeometry):
                raise ValueError("Map research area requires canonical geometry")
            features = self.aoi.to_collection()["features"]
            if len(features) != 1 or features[0]["geometry"]["type"] not in {
                "Polygon",
                "MultiPolygon",
            }:
                raise ValueError("Map research area requires one polygon or multipolygon")
            geometries.append(self.aoi)
        if (
            sum(item.feature_count for item in geometries) > 2000
            or sum(item.display_vertices for item in geometries) > 100_000
            or sum(len(item.canonical_json.encode("utf-8")) for item in geometries)
            > 5 * 1024 * 1024
        ):
            raise ValueError("Combined map geometry exceeds the view budget")


@dataclass(frozen=True, slots=True)
class MapView:
    id: UUID
    report_id: UUID
    created_by: UUID
    team_id: UUID | None
    latest_revision_id: UUID
    created_at: datetime
    archived: bool = False


@dataclass(frozen=True, slots=True)
class MapViewRevision:
    id: UUID
    view_id: UUID
    number: int
    title: str
    report_version_id: UUID
    report_version_number: int
    state: MapViewState
    evidence_sha256: str
    content_sha256: str
    created_by: UUID
    created_at: datetime

    def __post_init__(self) -> None:
        bounded_text(self.title, 200, "view title")
        if self.number < 1 or self.report_version_number < 1:
            raise ValueError("Map revision numbers must be positive")


@dataclass(frozen=True, slots=True)
class MapViewSummary:
    view: MapView
    title: str
    revision_number: int
    report_version_number: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MapViewPage:
    items: tuple[MapViewSummary, ...]
    total: int
    offset: int
    limit: int
