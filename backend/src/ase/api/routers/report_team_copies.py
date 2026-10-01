"""Copy a finished personal report version into a team and read the copy's provenance."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_report_team_copies import (
    TeamCopyIn,
    TeamCopyOut,
    TeamCopyPreviewOut,
    TeamCopyProvenanceOut,
)
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/reports/{report_id}", tags=["reports"])

VersionNumber = Annotated[int, Path(ge=1, le=100_000)]


@router.get("/versions/{number}/team-copy-preview")
async def preview_team_copy(
    report_id: UUID,
    number: VersionNumber,
    team_id: Annotated[UUID, Query()],
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> TeamCopyPreviewOut:
    preview = await container.report_team_copies(session).preview(user, report_id, number, team_id)
    response.headers["Cache-Control"] = "no-store"
    return await fence.release(TeamCopyPreviewOut.build(preview), session=session)


@router.post("/versions/{number}/team-copies", status_code=201)
async def copy_to_team(
    report_id: UUID,
    number: VersionNumber,
    body: TeamCopyIn,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> TeamCopyOut:
    result = await container.report_team_copies(session).copy(
        user,
        report_id,
        number,
        body.team_id,
        body.disclosed_evidence_labels,
        context,
        before_save=fence.confirm,
    )
    if not result.created:
        response.status_code = 200
    return await fence.release(TeamCopyOut.build(result), session=session)


@router.get("/team-copy-provenance")
async def team_copy_provenance(
    report_id: UUID,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> TeamCopyProvenanceOut:
    provenance = await container.report_team_copies(session).provenance(user, report_id)
    response.headers["Cache-Control"] = "no-store"
    return await fence.release(TeamCopyProvenanceOut.build(provenance), session=session)
