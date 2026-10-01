"""Administrator evaluation runs over packaged synthetic cases.

Mounted under ``/admin/llm`` by ``admin_llm_discovery``. Every route re-validates
the administrator's MFA-verified session through the release fence before it
returns run state or the download.
"""

from __future__ import annotations

from functools import partial
from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import AdminUser, ContainerDep, SessionDep
from ase.api.schemas_evaluations import (
    EvaluationCaseOut,
    EvaluationCatalogueOut,
    EvaluationRunOut,
    EvaluationRunsOut,
    EvaluationStartIn,
)
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/evaluations", tags=["admin"])


@router.get("/catalogue")
async def evaluation_catalogue(
    admin: AdminUser, session: SessionDep, fence: FenceDep, container: ContainerDep
) -> EvaluationCatalogueOut:
    cases = await container.evaluation_runs(session).catalogue(admin)
    body = EvaluationCatalogueOut(cases=[EvaluationCaseOut.from_case(case) for case in cases])
    return await fence.release(body, session=session, admin_only=True)


@router.get("")
async def list_evaluation_runs(
    admin: AdminUser, session: SessionDep, fence: FenceDep, container: ContainerDep
) -> EvaluationRunsOut:
    runs = await container.evaluation_runs(session).recent(admin)
    body = EvaluationRunsOut(items=[EvaluationRunOut.from_run(run) for run in runs])
    return await fence.release(body, session=session, admin_only=True)


@router.post("", status_code=202)
async def start_evaluation_run(
    body: EvaluationStartIn,
    admin: AdminUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
) -> EvaluationRunOut:
    run = await container.evaluation_runs(session).start(
        admin,
        body.to_input(),
        before_save=partial(fence.confirm, session=session, admin_only=True),
    )
    fence.assert_live()
    return EvaluationRunOut.from_run(run)


@router.get("/{run_id}")
async def get_evaluation_run(
    run_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
) -> EvaluationRunOut:
    run = await container.evaluation_runs(session).get(admin, run_id)
    return await fence.release(EvaluationRunOut.from_run(run), session=session, admin_only=True)


@router.post("/{run_id}/cancel")
async def cancel_evaluation_run(
    run_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
) -> EvaluationRunOut:
    run = await container.evaluation_runs(session).cancel(
        admin, run_id, before_save=partial(fence.confirm, session=session, admin_only=True)
    )
    fence.assert_live()
    return EvaluationRunOut.from_run(run)


@router.get(
    "/{run_id}/artefact",
    response_class=Response,
    responses={200: {"content": {"application/zip": {}}}},
)
async def download_evaluation_artefact(
    run_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
) -> Response:
    run, content = await container.evaluation_runs(session).artefact(admin, run_id)
    await fence.confirm(session=session, admin_only=True)
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="evaluation-{run.id}.zip"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
