"""Authenticated transient Eye answers from retained public map records."""

from fastapi import APIRouter, Request, Response

from ase.api.assistant_run import run_answer
from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_assistant import AssistantAnswerIn, AssistantAnswerOut
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.domain.errors import InvalidRequest

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/answer")
async def answer(
    request: Request,
    body: AssistantAnswerIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> AssistantAnswerOut:
    result = await run_answer(
        request,
        lambda: container.map_assistant(session).execute(
            user,
            body.to_question(),
            check_session=lambda: validate_request_session(container, claims),
        ),
    )
    async with container.source_admission.guard():
        identifiers = tuple(dict.fromkeys(source.source_id for source in result.context.sources))
        enabled = await container.source_admission.enabled_many(identifiers)
        if not all(enabled.get(identifier, False) for identifier in identifiers):
            raise InvalidRequest(
                "A source was disabled while answering. Ask again with current sources."
            )
        await validate_request_session(container, claims)
        payload = AssistantAnswerOut.from_answer(result)
        validate_request_expiry(container, claims)
        response.headers["Cache-Control"] = "private, no-store"
        return payload
