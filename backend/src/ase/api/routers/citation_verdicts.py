"""Human citation verdicts on one exact saved report version, and their JSONL export."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_citation_verdicts import (
    CitationVerdictIn,
    CitationVerdictListOut,
    CitationVerdictOut,
)
from ase.api.session_fence import FenceDep

router = APIRouter(
    prefix="/reports/{report_id}/versions/{number}/citation-verdicts",
    tags=["citation-verdicts"],
)
VersionNumber = Annotated[int, Path(ge=1, le=2_147_483_647)]


@router.get("")
async def list_verdicts(
    report_id: UUID,
    number: VersionNumber,
    _: CurrentUser,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> CitationVerdictListOut:
    result = await container.citation_verdicts(session).list(claims, report_id, number)
    response.headers["Cache-Control"] = "private, no-store"
    return await fence.release(CitationVerdictListOut.from_list(result), session=session)


@router.post("", status_code=201)
async def record_verdict(
    report_id: UUID,
    number: VersionNumber,
    body: CitationVerdictIn,
    _: CurrentUser,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> CitationVerdictOut:
    result = await container.citation_verdicts(session).record(
        claims, report_id, number, body.to_input(), context
    )
    response.headers["Cache-Control"] = "private, no-store"
    return await fence.release(CitationVerdictOut.from_verdict(result), session=session)


@router.get(
    "/export",
    response_class=Response,
    responses={200: {"content": {"application/x-ndjson": {"schema": {"type": "string"}}}}},
)
async def export_verdicts(
    report_id: UUID,
    number: VersionNumber,
    _: CurrentUser,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
) -> Response:
    result = await container.citation_verdicts(session).export(claims, report_id, number)
    content = await fence.release(result.content, session=session)
    return Response(
        content,
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
