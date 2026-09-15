"""Reports: generate from live evidence, read, export as Markdown, delete."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, Query, Request, Response

from ase.adapters.reports.async_documents import run_bounded_thread
from ase.adapters.reports.markdown_package import render_markdown_export
from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.report_reviewed_snapshot import selected_reviewed_snapshot
from ase.api.report_run import run_generation
from ase.api.schemas_reports import (
    ReportCreateIn,
    ReportOut,
    ReportsOut,
    ReportSummaryOut,
    TemplatesOut,
)
from ase.api.session_guard import validate_request_session
from ase.application.reports.document import build_document
from ase.application.reports.document_release import release_document
from ase.container.source_reviews import source_reviews

router = APIRouter(prefix="/reports", tags=["reports"])


def _media_quality(value: str, expected: str) -> float:
    accepted = 0.0
    for media_range in value.split(","):
        parts = [part.strip() for part in media_range.split(";")]
        if not parts or parts[0].casefold() != expected:
            continue
        quality = 1.0
        for parameter in parts[1:]:
            name, separator, raw_value = parameter.partition("=")
            if separator and name.strip().casefold() == "q":
                try:
                    quality = float(raw_value.strip())
                except ValueError:
                    quality = 0.0
        if 0.0 <= quality <= 1.0:
            accepted = max(accepted, quality)
    return accepted


def _prefers_zip(value: str) -> bool:
    return _media_quality(value, "application/zip") > _media_quality(value, "text/markdown")


@router.get("/templates")
async def list_templates(user: CurrentUser) -> TemplatesOut:
    return TemplatesOut.all()


@router.get("")
async def list_reports(
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ReportsOut:
    records = await container.list_reports(session).execute(user, limit)
    return ReportsOut(items=[ReportSummaryOut.from_record(record) for record in records])


@router.post("", status_code=201)
async def create_report(
    request: Request,
    body: ReportCreateIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    background: BackgroundTasks,
    run_id: Annotated[UUID | None, Header(alias="X-Research-Run-ID")] = None,
) -> ReportOut:
    record, version = await run_generation(
        request,
        user,
        container.research_runs,
        run_id,
        lambda progress: container.generate_report(session).execute(
            user, body.to_request(), context, progress=progress
        ),
        before_save=lambda: validate_request_session(container, claims),
    )
    background.add_task(container.archive_report_version, version)
    return await run_bounded_thread(lambda: ReportOut.build(record, version), wait_for_slot=True)


@router.post("/{report_id}/versions", status_code=201)
async def regenerate_report(
    request: Request,
    report_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    background: BackgroundTasks,
    run_id: Annotated[UUID | None, Header(alias="X-Research-Run-ID")] = None,
) -> ReportOut:
    record, version = await run_generation(
        request,
        user,
        container.research_runs,
        run_id,
        lambda progress: container.generate_report(session).regenerate(
            user, report_id, context, progress=progress
        ),
        before_save=lambda: validate_request_session(container, claims),
    )
    background.add_task(container.archive_report_version, version)
    return await run_bounded_thread(lambda: ReportOut.build(record, version), wait_for_slot=True)


@router.get("/{report_id}")
async def get_report(
    report_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    version: Annotated[int | None, Query(ge=1)] = None,
    source_snapshot_id: UUID | None = None,
) -> ReportOut:
    record, found = await container.get_report(session).execute(user, report_id, version)
    snapshot = await selected_reviewed_snapshot(
        claims, container, session, record, found, version, source_snapshot_id
    )
    result = await run_bounded_thread(lambda: ReportOut.build(record, found, snapshot))
    if snapshot is not None:
        await selected_reviewed_snapshot(
            claims, container, session, record, found, version, source_snapshot_id
        )
    return result


@router.get(
    "/{report_id}/markdown",
    response_class=Response,
    responses={
        200: {
            "content": {
                "text/markdown": {"schema": {"type": "string"}},
                "application/zip": {"schema": {"type": "string", "format": "binary"}},
            }
        }
    },
)
async def report_markdown(
    report_id: UUID,
    request: Request,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    version: Annotated[int | None, Query(ge=1)] = None,
    source_snapshot_id: UUID | None = None,
) -> Response:
    record, found = await container.get_report(session).execute(user, report_id, version)
    snapshot = await selected_reviewed_snapshot(
        claims, container, session, record, found, version, source_snapshot_id
    )
    package_figures = _prefers_zip(request.headers.get("accept", ""))
    rendered = await run_bounded_thread(
        lambda: render_markdown_export(
            build_document(record, found, reviewed_snapshot=snapshot),
            report_id,
            found.id,
            found.number,
            package_figures=package_figures,
        )
    )
    repositories = container.repositories(session)
    await release_document(
        claims,
        report_id,
        rendered,
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
        rendered.content,
        media_type=rendered.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{rendered.filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{report_id}", status_code=204, response_class=Response)
async def delete_report(
    report_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.delete_report(session).execute(user, report_id, context)
    return Response(status_code=204)
