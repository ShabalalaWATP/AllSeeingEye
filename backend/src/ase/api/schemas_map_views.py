"""Typed saved-map transport with canonical geometry validation at the boundary."""

from datetime import date, datetime
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from ase.domain.map_view_records import state_from_dict, state_to_dict
from ase.domain.map_views import MapView, MapViewPage, MapViewRevision, MapViewState, bounded_text


class MapFields(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class MapCameraFields(MapFields):
    longitude: float = Field(ge=-180, le=180, strict=True, allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90, strict=True, allow_inf_nan=False)
    zoom: float = Field(ge=0, le=22, strict=True, allow_inf_nan=False)
    bearing: float = Field(default=0, ge=-180, le=180, strict=True, allow_inf_nan=False)
    pitch: float = Field(default=0, ge=0, le=60, strict=True, allow_inf_nan=False)


class MapOverlayFields(MapFields):
    geometry: dict[str, Any]
    source: str = Field(min_length=1, max_length=200)
    dataset_date: date
    attribution: str = Field(min_length=1, max_length=500)
    precision: Literal["exact", "approximate", "unknown"]
    visible: bool = Field(default=True, strict=True)


class MapStateFields(MapFields):
    camera: MapCameraFields
    projection: Literal["globe", "mercator"] = "globe"
    basemap: Literal[
        "dark", "streets", "light", "satellite", "hybrid", "os_road", "os_outdoor", "os_light"
    ] = "dark"
    source_ids: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(
        default_factory=list, max_length=64
    )
    published_since: AwareDatetime | None = None
    published_until: AwareDatetime | None = None
    include_unknown_dates: bool = Field(default=True, strict=True)
    selected_evidence: str | None = Field(default=None, min_length=1, max_length=128)
    overlays: list[MapOverlayFields] = Field(default_factory=list, max_length=8)
    aoi: dict[str, Any] | None = None
    schema_version: Annotated[int, Field(strict=True, ge=1, le=1)] = 1
    display_transform: Literal["ase-geojson-display-v1", "ase-geojson-display-v2"] = (
        "ase-geojson-display-v1"
    )
    _domain: MapViewState = PrivateAttr()

    @model_validator(mode="after")
    def validate_canonical_state(self) -> Self:
        # Pydantic turns ValueError into a validation response, never a server error.
        self._domain = state_from_dict(self.model_dump(mode="json"))
        return self

    def to_domain(self) -> MapViewState:
        return self._domain


class MapSaveFields(MapFields):
    version_number: int = Field(ge=1, strict=True)
    title: str = Field(min_length=1, max_length=200)
    state: MapStateFields

    @model_validator(mode="after")
    def validate_title(self) -> Self:
        bounded_text(self.title, 200, "view title")
        return self


class MapViewCreateIn(MapSaveFields):
    report_id: UUID


class MapViewUpdateIn(MapSaveFields):
    base_revision_id: UUID


class MapViewOut(MapFields):
    id: UUID
    report_id: UUID
    created_by: UUID
    team_id: UUID | None
    latest_revision_id: UUID
    created_at: datetime
    archived: bool


class MapRevisionOut(MapFields):
    id: UUID
    view_id: UUID
    number: int
    title: str
    report_version_id: UUID
    report_version_number: int
    state: MapStateFields
    evidence_sha256: str
    content_sha256: str
    created_by: UUID
    created_at: datetime


class SavedMapViewOut(MapFields):
    view: MapViewOut
    revision: MapRevisionOut

    @classmethod
    def build(cls, view: MapView, revision: MapViewRevision) -> Self:
        return cls(
            view=MapViewOut.model_validate(view),
            revision=MapRevisionOut(
                id=revision.id,
                view_id=revision.view_id,
                number=revision.number,
                title=revision.title,
                report_version_id=revision.report_version_id,
                report_version_number=revision.report_version_number,
                state=MapStateFields.model_validate(state_to_dict(revision.state)),
                evidence_sha256=revision.evidence_sha256,
                content_sha256=revision.content_sha256,
                created_by=revision.created_by,
                created_at=revision.created_at,
            ),
        )


class MapViewSummaryOut(MapFields):
    view: MapViewOut
    title: str
    revision_number: int
    report_version_number: int
    updated_at: datetime


class MapViewPageOut(MapFields):
    items: list[MapViewSummaryOut]
    total: int
    offset: int
    limit: int

    @classmethod
    def build(cls, page: MapViewPage) -> Self:
        return cls(
            items=[MapViewSummaryOut.model_validate(item) for item in page.items],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
        )
