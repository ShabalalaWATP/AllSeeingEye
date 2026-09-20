"""Explicit private save, resume and delete for Ask Eye conversations."""

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_assistant_history import (
    SavedConversationIn,
    SavedConversationOut,
    SavedConversationPageOut,
    SavedConversationSummaryOut,
    conversation_out,
    report_references,
)
from ase.api.session_guard import validate_request_expiry, validate_request_session

router = APIRouter(prefix="/assistant/conversations", tags=["assistant"])


@router.get("")
async def list_conversations(
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SavedConversationPageOut:
    rows = await container.assistant_history(session).list(user)
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
    service = container.assistant_history(session)
    record = await service.save(
        user, body.title, [turn.safe_dict() for turn in body.turns], report_references(body.turns)
    )
    result = conversation_out(record)
    await service.authorise_reports(user, report_references(result.turns))
    validate_request_expiry(container, claims)
    await service.commit()
    await service.authorise_reports(user, report_references(result.turns))
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
    service = container.assistant_history(session)
    record = await service.get(user, conversation_id)
    await validate_request_session(container, claims)
    result = conversation_out(record)
    await service.authorise_reports(user, report_references(result.turns))
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
    service = container.assistant_history(session)
    record = await service.save(
        user,
        body.title,
        [turn.safe_dict() for turn in body.turns],
        report_references(body.turns),
        conversation_id,
    )
    result = conversation_out(record)
    await service.authorise_reports(user, report_references(result.turns))
    validate_request_expiry(container, claims)
    await service.commit()
    await service.authorise_reports(user, report_references(result.turns))
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
    service = container.assistant_history(session)
    await service.remove(user, conversation_id)
    validate_request_expiry(container, claims)
    await service.commit()
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    return Response(status_code=204, headers={"Cache-Control": "private, no-store"})
