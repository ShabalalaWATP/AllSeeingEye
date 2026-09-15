"""Read one selected original excerpt under current report and source authority."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.adapters.persistence.original_passages import SqlOriginalPassageRepository
from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_original_passages import OriginalPassageOut
from ase.api.session_guard import validate_request_session
from ase.domain.errors import NotFound

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
    report, version = await container.get_report(session).execute(user, report_id, version_number)
    receipt = version.research
    linked = (
        next(
            (
                row
                for row in receipt.original_followup
                if row.passage_ref == passage_ref and row.status == "acquired"
            ),
            None,
        )
        if receipt is not None
        else None
    )
    if linked is None:
        raise NotFound()
    item = next((row for row in version.evidence if row.label == linked.evidence_label), None)
    if item is None or (item.event_id, item.source_id) != (linked.event_id, linked.source_id):
        raise NotFound()
    now = container.clock.now()
    staged = await SqlOriginalPassageRepository(session).linked(passage_ref, version.id, now)
    if (
        staged is None
        or staged.job_id is None
        or staged.document.owner_id != report.created_by
        or staged.document.team_id != report.team_id
        or staged.evidence_label != linked.evidence_label
        or staged.event_id != linked.event_id
        or staged.document.id != linked.document_version_id
        or staged.document.passages[0].id != linked.passage_id
    ):
        raise NotFound()
    document = staged.document
    policy = getattr(container, "original_source_policies", {}).get(document.source_id)
    async with container.source_admission.guard():
        if (
            policy is None
            or policy.policy_id != document.acquisition_policy_id
            or not policy.permits(document.canonical_url, container.clock.now())
            or not await container.source_admission.enabled(document.source_id)
        ):
            raise NotFound()
        await container.get_report(session).recheck(user, report_id, version.number)
        await validate_request_session(container, claims)
    passage = document.passages[0]
    response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
    return OriginalPassageOut(
        ref=staged.id,
        evidence_label=linked.evidence_label,
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
