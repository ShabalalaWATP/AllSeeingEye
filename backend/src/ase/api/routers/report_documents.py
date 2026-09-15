"""Authenticated offline report exports and comparisons of versions of one report."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.report_reviewed_snapshot import selected_reviewed_snapshot
from ase.api.schemas_claim_export import ClaimPackageIn
from ase.api.schemas_report_documents import ReportComparisonOut
from ase.api.session_guard import validate_request_session
from ase.application.reports.document_release import release_document
from ase.container.source_reviews import source_reviews
from ase.domain.report_documents import ExportFormat

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/{report_id}/selected-evidence-package",
    response_class=Response,
    responses={
        200: {"content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}}}
    },
)
@router.post(
    "/{report_id}/claim-evidence-package",
    response_class=Response,
    responses={
        200: {"content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}}}
    },
)
async def export_claim_evidence_package(
    report_id: UUID,
    body: ClaimPackageIn,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
) -> Response:
    if body.asset_ids:
        # The asset use case performs the final combined lifecycle/session check.
        # Keep this separate request guard before that final transaction.
        await validate_request_session(container, claims)
    result = await container.export_claim_package(session).execute(
        claims,
        report_id,
        body.version_number,
        body.references(),
        identity_references=body.identity_references(),
        relationship_references=body.relationship_references(),
        asset_ids=tuple(body.asset_ids),
    )
    if not body.asset_ids:
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
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    version: Annotated[int | None, Query(ge=1)] = None,
    source_snapshot_id: UUID | None = None,
) -> Response:
    snapshot = None
    if source_snapshot_id is not None:
        record, found = await container.get_report(session).execute(user, report_id, version)
        snapshot = await selected_reviewed_snapshot(
            claims, container, session, record, found, version, source_snapshot_id
        )
    exporter = container.export_report(session)
    result = (
        await exporter.execute(user, report_id, format, version)
        if snapshot is None
        else await exporter.execute(user, report_id, format, version, snapshot)
    )
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
        source_reviews=source_reviews(container, session).reviews if snapshot is not None else None,
        source_snapshot_id=snapshot.id if snapshot is not None else None,
    )
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
