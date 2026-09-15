"""Explicit private save, resume and delete for Ask Eye conversations."""

import json
from collections.abc import Iterable
from uuid import UUID

from fastapi import APIRouter, Response

from ase.adapters.persistence.assistant_history import SqlAssistantHistory
from ase.adapters.persistence.assistant_history_models import AssistantConversationRow
from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_assistant_history import (
    SavedConversationIn,
    SavedConversationOut,
    SavedConversationPageOut,
    SavedConversationSummaryOut,
    SavedTurnIn,
    SavedTurnOut,
)
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.domain.errors import NotFound

router = APIRouter(prefix="/assistant/conversations", tags=["assistant"])


def _out(row: AssistantConversationRow) -> SavedConversationOut:
    turns = json.loads(row.transcript)["turns"]
    for turn in turns:
        # Resume fits the regular answer contract, without persisting transient
        # continuation authority or administrator-only model details.
        turn["answer"]["continuation_id"] = None
        turn["answer"]["model"] = None
    return SavedConversationOut(
        id=row.id,
        title=row.title,
        turns=turns,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _authorise_report_turns(
    user: CurrentUser,
    turns: Iterable[SavedTurnIn | SavedTurnOut],
    container: ContainerDep,
    session: SessionDep,
) -> None:
    references = {
        (turn.report.id, turn.report.version)
        for turn in turns
        if turn.scope == "report" and turn.report is not None
    }
    if not references:
        return
    reports = container.get_report(session)
    for report_id, version in references:
        await reports.execute(user, report_id, version)


@router.get("")
async def list_conversations(
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SavedConversationPageOut:
    rows = await SqlAssistantHistory(session).list(user.id)
    await validate_request_session(container, claims)
    result = SavedConversationPageOut(
        items=[
            SavedConversationSummaryOut(
                id=row.id,
                title=row.title,
                turn_count=row.turn_count,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
    )
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.post("", status_code=201)
async def save_conversation(
    body: SavedConversationIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SavedConversationOut:
    # A separate validation session after an uncommitted write can share the
    # SQLite in-memory connection and roll back that write. Check first, then
    # recheck after commit before releasing the private snapshot.
    await validate_request_session(container, claims)
    await _authorise_report_turns(user, body.turns, container, session)
    record = await SqlAssistantHistory(session).create(
        user.id, body.title, [turn.safe_dict() for turn in body.turns], container.clock.now()
    )
    result = _out(record)
    await _authorise_report_turns(user, result.turns, container, session)
    validate_request_expiry(container, claims)
    await session.commit()
    await _authorise_report_turns(user, result.turns, container, session)
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SavedConversationOut:
    row = await SqlAssistantHistory(session).get(user.id, conversation_id)
    if row is None:
        raise NotFound()
    await validate_request_session(container, claims)
    result = _out(row)
    await _authorise_report_turns(user, result.turns, container, session)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.put("/{conversation_id}")
async def replace_conversation(
    conversation_id: UUID,
    body: SavedConversationIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SavedConversationOut:
    await validate_request_session(container, claims)
    await _authorise_report_turns(user, body.turns, container, session)
    row = await SqlAssistantHistory(session).update(
        user.id,
        conversation_id,
        body.title,
        [turn.safe_dict() for turn in body.turns],
        container.clock.now(),
    )
    result = _out(row)
    await _authorise_report_turns(user, result.turns, container, session)
    validate_request_expiry(container, claims)
    await session.commit()
    await _authorise_report_turns(user, result.turns, container, session)
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
) -> Response:
    await validate_request_session(container, claims)
    if not await SqlAssistantHistory(session).remove(user.id, conversation_id):
        raise NotFound()
    validate_request_expiry(container, claims)
    await session.commit()
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    return Response(status_code=204, headers={"Cache-Control": "private, no-store"})
