"""Reports: generate from live evidence, read, export as Markdown, delete."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, Query, Request, Response
from fastapi.responses import PlainTextResponse

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.report_run import run_generation
from ase.api.schemas_reports import (
    ReportCreateIn,
    ReportOut,
    ReportsOut,
    ReportSummaryOut,
    TemplatesOut,
)
from ase.api.session_guard import validate_request_session

router = APIRouter(prefix="/reports", tags=["reports"])


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
    return ReportOut.build(record, version)


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
    return ReportOut.build(record, version)


@router.get("/{report_id}")
async def get_report(
    report_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    version: Annotated[int | None, Query(ge=1)] = None,
) -> ReportOut:
    record, found = await container.get_report(session).execute(user, report_id, version)
    return ReportOut.build(record, found)


@router.get("/{report_id}/markdown", response_class=PlainTextResponse)
async def report_markdown(
    report_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    version: Annotated[int | None, Query(ge=1)] = None,
) -> PlainTextResponse:
    _, found = await container.get_report(session).execute(user, report_id, version)
    return PlainTextResponse(found.markdown, media_type="text/markdown; charset=utf-8")


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
