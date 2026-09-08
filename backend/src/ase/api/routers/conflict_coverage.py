"""Safe, authenticated conflict-source coverage without provider diagnostics."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ase.api.deps import ContainerDep, CurrentUser
from ase.application.feeds.health import SourceStatus

router = APIRouter()

# Public editorial descriptions, never derived from upstream errors or URLs.
DESCRIPTIONS = (
    (
        "gdelt_events",
        "GDELT events",
        "Early reporting",
        "Machine-coded media reports; latest export is bounded. Source counts do not "
        "establish independent confirmation.",
    ),
    (
        "ucdp_candidate",
        "UCDP Candidate",
        "Historical baseline",
        "Provisional monthly research release. Occurrence dates determine activity; "
        "this is not a live incident feed.",
    ),
    (
        "acled_events",
        "ACLED",
        "Coded incidents",
        "Requires approved data access and a valid token. Includes protests and "
        "other activity separately from violence.",
    ),
    (
        "reliefweb_reports",
        "ReliefWeb API",
        "Humanitarian context",
        "Requires an approved application name. Original publishers retain "
        "ownership; reports are not additional confirmed incidents.",
    ),
    (
        "reliefweb_updates",
        "ReliefWeb RSS",
        "Humanitarian context",
        "Humanitarian reporting and original-source links; availability depends on "
        "the public feed.",
    ),
    (
        "crisis_group",
        "International Crisis Group",
        "Analysis",
        "Analytical context, not a geolocated attack feed or independent "
        "confirmation of every incident.",
    ),
)


class ConflictSourceOut(BaseModel):
    id: str
    name: str
    role: str
    status: Literal["configured", "waiting", "not_configured", "healthy", "degraded"]
    detail: str
    dataset_release: str | None = None
    last_success: datetime | None = None


class ConflictSourcesOut(BaseModel):
    items: list[ConflictSourceOut]


@router.get("/conflict-sources")
async def conflict_sources(user: CurrentUser, container: ContainerDep) -> ConflictSourcesOut:
    specs = {connector.spec.id: connector.spec for connector in container.connectors}
    enabled = await container.source_admission.enabled_many(tuple(row[0] for row in DESCRIPTIONS))
    health = {entry.source_id: entry for entry in container.health.snapshot()}
    items: list[ConflictSourceOut] = []
    for source_id, name, role, description in DESCRIPTIONS:
        detail = description
        status: Literal["configured", "waiting", "not_configured", "healthy", "degraded"] = (
            "not_configured"
        )
        entry = health.get(source_id)
        if source_id in specs:
            status = "waiting"
            if not enabled.get(source_id, True):
                status, detail = (
                    "not_configured",
                    detail + " Collection is disabled by an administrator.",
                )
            elif entry is not None:
                if entry.status is SourceStatus.HEALTHY:
                    status = "healthy"
                elif entry.status in (SourceStatus.DEGRADED, SourceStatus.DISABLED):
                    status = "degraded"
        items.append(
            ConflictSourceOut(
                id=source_id,
                name=name,
                role=role,
                status=status,
                detail=detail,
                dataset_release=container.settings.ucdp_candidate_version
                if source_id == "ucdp_candidate"
                else None,
                last_success=entry.last_success if entry else None,
            )
        )
    return ConflictSourcesOut(items=items)
