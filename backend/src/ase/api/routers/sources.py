"""Authenticated source context and connection state without operator URLs or credentials."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_source_ratings import SourceRatingOut
from ase.application.feeds.health import SourceHealth, SourceStatus
from ase.application.source_assets import AssetDelivery, AssetFamily, SourceAsset
from ase.application.source_inventory import (
    ConnectionState,
    InventoryEntry,
    PlatformConnection,
    RequirementKind,
    RequirementOrigin,
    SourceConnection,
    SourceRequirement,
)
from ase.domain.events import Category, Reliability
from ase.domain.source_discovery import CoverageScope, source_coverage
from ase.domain.source_ratings import unassessed_source_rating
from ase.domain.sources import SourceKind

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceRequirementOut(BaseModel):
    kind: RequirementKind
    satisfied: bool | None
    origin: RequirementOrigin
    setting: str | None
    note: str
    optional: bool

    @classmethod
    def from_requirement(cls, value: SourceRequirement) -> "SourceRequirementOut":
        return cls(
            kind=value.kind,
            satisfied=value.satisfied,
            origin=value.origin,
            setting=value.setting,
            note=value.note,
            optional=value.optional,
        )


class SourceHealthSummaryOut(BaseModel):
    """Delivery health without error text, which can embed operator URLs.

    `blocked_reason` is fixed server-authored text for an upstream refusal, never raw error text.
    """

    status: SourceStatus
    last_success: datetime | None
    last_error_at: datetime | None
    consecutive_failures: int
    items_last_poll: int
    next_poll_at: datetime | None
    polls: int
    blocked_reason: str | None

    @classmethod
    def from_health(cls, value: SourceHealth) -> "SourceHealthSummaryOut":
        return cls(
            status=value.status,
            last_success=value.last_success,
            last_error_at=value.last_error_at,
            consecutive_failures=value.consecutive_failures,
            items_last_poll=value.items_last_poll,
            next_poll_at=value.next_poll_at,
            polls=value.polls,
            blocked_reason=value.blocked_reason,
        )


class SourceConnectionOut(BaseModel):
    state: ConnectionState
    enabled: bool
    environment_disabled: bool
    active: bool
    requirement: SourceRequirementOut | None
    health: SourceHealthSummaryOut | None
    detail: str

    @classmethod
    def from_connection(cls, value: SourceConnection) -> "SourceConnectionOut":
        return cls(
            state=value.state,
            enabled=value.enabled,
            environment_disabled=value.environment_disabled,
            active=value.active,
            requirement=(
                SourceRequirementOut.from_requirement(value.requirement)
                if value.requirement
                else None
            ),
            health=SourceHealthSummaryOut.from_health(value.health) if value.health else None,
            detail=value.detail,
        )


class SourceSummaryOut(BaseModel):
    id: str
    name: str
    organisation: str
    parent_organisation: str | None
    category: Category
    language: str
    reliability: Reliability
    rating: SourceRatingOut
    kind: SourceKind
    requires_key: bool
    collection_mode: Literal["on_demand", "scheduled"]
    coverage_scope: CoverageScope
    coverage_countries: list[str]
    coverage_regions: list[str]
    coverage_note: str
    connection: SourceConnectionOut

    @classmethod
    def from_entry(cls, entry: InventoryEntry) -> "SourceSummaryOut":
        spec = entry.spec
        coverage = source_coverage(spec.id)
        return cls(
            id=spec.id,
            name=spec.name,
            organisation=spec.organisation,
            parent_organisation=spec.parent_organisation,
            category=spec.category,
            language=spec.language,
            reliability=spec.reliability,
            rating=SourceRatingOut.model_validate(spec.rating or unassessed_source_rating()),
            kind=spec.kind,
            requires_key=spec.requires_key,
            collection_mode=entry.collection_mode,
            coverage_scope=coverage.scope,
            coverage_countries=list(coverage.countries),
            coverage_regions=list(coverage.regions),
            coverage_note=coverage.note,
            connection=SourceConnectionOut.from_connection(entry.connection),
        )


class SourceAssetOut(BaseModel):
    """A camera index, map layer or dataset: public publisher metadata and state only."""

    id: str
    name: str
    family: AssetFamily
    delivery: AssetDelivery
    organisation: str
    description: str
    licence_note: str
    homepage: str | None
    coverage_note: str
    refresh_note: str
    state: ConnectionState
    detail: str
    requirement: SourceRequirementOut | None
    as_of: str | None
    records: int | None

    @classmethod
    def from_asset(cls, value: SourceAsset) -> "SourceAssetOut":
        return cls(
            id=value.id,
            name=value.name,
            family=value.family,
            delivery=value.delivery,
            organisation=value.organisation,
            description=value.description,
            licence_note=value.licence_note,
            homepage=value.homepage if (value.homepage or "").startswith("https://") else None,
            coverage_note=value.coverage_note,
            refresh_note=value.refresh_note,
            state=value.state,
            detail=value.detail,
            requirement=(
                SourceRequirementOut.from_requirement(value.requirement)
                if value.requirement
                else None
            ),
            as_of=value.as_of,
            records=value.records,
        )


class SourcesOut(BaseModel):
    items: list[SourceSummaryOut]
    assets: list[SourceAssetOut] = []


class PlatformConnectionOut(BaseModel):
    id: str
    name: str
    purpose: str
    state: ConnectionState
    requirement: SourceRequirementOut
    detail: str

    @classmethod
    def from_connection(cls, value: PlatformConnection) -> "PlatformConnectionOut":
        return cls(
            id=value.id,
            name=value.name,
            purpose=value.purpose,
            state=value.state,
            requirement=SourceRequirementOut.from_requirement(value.requirement),
            detail=value.detail,
        )


class PlatformConnectionsOut(BaseModel):
    items: list[PlatformConnectionOut]


@router.get("")
async def list_sources(
    user: CurrentUser, container: ContainerDep, session: SessionDep, response: Response
) -> SourcesOut:
    response.headers["Cache-Control"] = "private, no-store"
    entries = await container.source_inventory(session).list()
    assets = container.source_assets(user)
    return SourcesOut(
        items=[SourceSummaryOut.from_entry(entry) for entry in entries],
        assets=[SourceAssetOut.from_asset(asset) for asset in assets],
    )


@router.get("/connections")
async def list_connections(
    user: CurrentUser, container: ContainerDep, session: SessionDep, response: Response
) -> PlatformConnectionsOut:
    response.headers["Cache-Control"] = "private, no-store"
    rows = await container.platform_connections(session, user)
    return PlatformConnectionsOut(
        items=[PlatformConnectionOut.from_connection(row) for row in rows]
    )
