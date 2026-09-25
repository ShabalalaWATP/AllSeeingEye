"""Authenticated transient Eye answers from retained public map records."""

from fastapi import APIRouter, Request, Response

from ase.api.assistant_run import run_answer
from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_assistant import AssistantAnswerIn, AssistantAnswerOut
from ase.api.session_fence import FenceDep
from ase.application.assistant.report_context import ReportContextReader
from ase.domain.errors import InvalidRequest

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/answer")
async def answer(
    request: Request,
    body: AssistantAnswerIn,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> AssistantAnswerOut:
    result = await run_answer(
        request,
        lambda: container.map_assistant(session).execute(
            user,
            body.to_question(),
            check_session=fence.confirm,
        ),
    )
    async with container.source_admission.guard():
        identifiers = tuple(
            dict.fromkeys(
                source.source_id
                for source in result.context.sources
                if source.kind != "report_claim"
            )
        )
        enabled = await container.source_admission.enabled_many(identifiers)
        if not all(enabled.get(identifier, False) for identifier in identifiers):
            raise InvalidRequest(
                "A source was disabled while answering. Ask again with current sources."
            )
        if result.context.report is not None:
            await ReportContextReader(container.get_report(session)).require_current(
                user, result.context.report
            )
        await fence.confirm()
        payload = AssistantAnswerOut.from_answer(result)
        fence.assert_live()
        response.headers["Cache-Control"] = "private, no-store"
        return payload
