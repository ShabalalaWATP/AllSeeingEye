"""Private SEC primary-document import and transient inert original downloads."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from ase.api.deps import ClaimsDep, ContainerDep, SessionDep, get_current_user
from ase.api.routers.research_inputs import _complete_connected
from ase.api.schemas_research_inputs import ResearchInputOut
from ase.api.schemas_sec_filings import SecFilingChoiceOut, SecFilingsPageOut, SecFilingsSearchIn
from ase.api.session_guard import validate_request_expiry

router = APIRouter(
    prefix="/research/sec/filings", tags=["research"], dependencies=[Depends(get_current_user)]
)


@router.post("")
async def list_filings(
    body: SecFilingsSearchIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    request: Request,
) -> SecFilingsPageOut:
    page, choices = await _complete_connected(
        request,
        container.sec_filings(session).list(
            claims, body.cik, body.since, body.until, body.archive_page, body.offset
        ),
    )
    await container.sec_filings(session).release_choices(claims, choices)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return SecFilingsPageOut(
        items=[SecFilingChoiceOut.from_choice(value) for value in choices],
        archive_page=page.archive_page,
        archive_pages=page.archive_pages,
        offset=page.offset,
        next_offset=page.next_offset,
        limitations=list(page.limitations),
    )


@router.post("/{selection_id}/import", status_code=201)
async def import_filing(
    selection_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    request: Request,
    response: Response,
) -> ResearchInputOut:
    result = await _complete_connected(
        request, container.sec_filings(session).import_filing(claims, selection_id)
    )
    result = await container.sec_filings(session).release_input(claims, selection_id, result.id)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return ResearchInputOut.from_receipt(result, ())


@router.get("/{selection_id}/original")
async def original_filing(
    selection_id: UUID, claims: ClaimsDep, container: ContainerDep, session: SessionDep
) -> Response:
    filename, data = await container.sec_filings(session).original(claims, selection_id)
    validate_request_expiry(container, claims)
    return Response(
        data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'",
        },
    )
