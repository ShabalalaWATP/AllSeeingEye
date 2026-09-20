"""Read one selected original excerpt under current report and source authority."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_original_passages import OriginalPassageOut
from ase.api.session_guard import validate_request_session

router = APIRouter(prefix="/reports/{report_id}/original-passages", tags=["reports"])


@router.get("/{passage_ref}")
async def read_original_passage(
    report_id: UUID,
    passage_ref: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    version_number: Annotated[int, Query(ge=1)],
) -> OriginalPassageOut:
    await validate_request_session(container, claims)
    staged = await container.original_passage_reader(session).execute(
        user,
        report_id,
        version_number,
        passage_ref,
        lambda: validate_request_session(container, claims),
    )
    document = staged.document
    passage = document.passages[0]
    response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
    return OriginalPassageOut(
        ref=staged.id,
        evidence_label=staged.evidence_label,
        source_id=document.source_id,
        issuer=document.issuer,
        document_version_id=document.id,
        original_sha256=document.sha256,
        passage_id=passage.id,
        passage_sha256=passage.text_sha256,
        source_reference=passage.source_reference,
        page=passage.page,
        text=passage.text,
        published_at=document.published_at,
        retrieved_at=document.retrieved_at,
        expires_at=document.expires_at,
        original_language=document.original_language,
        permitted_use=document.permitted_use,
    )
