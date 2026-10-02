"""Frozen STIX export with exact-version and current-session release fencing."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.adapters.reports.stix import FrozenStixRenderer
from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.session_fence import FenceDep
from ase.application.reports.document_release import release_document
from ase.application.reports.stix import ExportStix
from ase.domain.stix import StixTlp

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{report_id}/stix", response_class=Response)
async def export_stix(
    report_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
    version: Annotated[int, Query(ge=1)],
    tlp: StixTlp,
) -> Response:
    result = await ExportStix(container.get_report(session), FrozenStixRenderer()).execute(
        user, report_id, version, tlp
    )
    await fence.confirm()
    repositories = container.repositories(session)
    await release_document(
        claims,
        report_id,
        result,
        users=repositories.users,
        refresh=repositories.refresh_tokens,
        reports=repositories.reports,
        access=container.access_policy(session),
        clock=container.clock,
        uow=repositories.uow,
    )
    fence.assert_live()
    return Response(
        result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
