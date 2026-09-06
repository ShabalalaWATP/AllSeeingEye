"""Authenticated offline report exports and comparisons of versions of one report."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_report_documents import ReportComparisonOut
from ase.api.session_guard import validate_request_session
from ase.domain.report_documents import ExportFormat

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{report_id}/evidence-package", response_class=Response)
async def export_evidence_package(
    report_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    version: Annotated[int | None, Query(ge=1)] = None,
) -> Response:
    result = await container.export_evidence_package(session).execute(user, report_id, version)
    await validate_request_session(container, claims)
    return Response(
        result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{report_id}/export/{format}",
    response_class=Response,
    responses={
        200: {
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}},
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "schema": {"type": "string", "format": "binary"}
                },
            }
        }
    },
)
async def export_report(
    report_id: UUID,
    format: ExportFormat,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    version: Annotated[int | None, Query(ge=1)] = None,
) -> Response:
    result = await container.export_report(session).execute(user, report_id, format, version)
    return Response(
        result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{report_id}/diff")
async def compare_report_versions(
    report_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    from_version: Annotated[int, Query(ge=1)],
    to_version: Annotated[int, Query(ge=1)],
) -> ReportComparisonOut:
    result = await container.compare_reports(session).execute(
        user, report_id, from_version, to_version
    )
    return ReportComparisonOut.model_validate(result)
