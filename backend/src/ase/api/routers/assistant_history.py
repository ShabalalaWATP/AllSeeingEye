"""Explicit private save, resume and delete for Ask Eye conversations."""

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_assistant_history import (
    SavedConversationIn,
    SavedConversationOut,
    SavedConversationPageOut,
    SavedConversationSummaryOut,
    conversation_out,
    report_references,
)
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/assistant/conversations", tags=["assistant"])


@router.get("")
async def list_conversations(
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> SavedConversationPageOut:
    rows = await container.assistant_history(session).list(user)
    await fence.confirm()
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
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.post("", status_code=201)
async def save_conversation(
    body: SavedConversationIn,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> SavedConversationOut:
    # A separate validation session after an uncommitted write can share the
    # SQLite in-memory connection and roll back that write. Check first, then
    # recheck after commit before releasing the private snapshot.
    await fence.confirm()
    service = container.assistant_history(session)
    record = await service.save(
        user, body.title, [turn.safe_dict() for turn in body.turns], report_references(body.turns)
    )
    result = conversation_out(record)
    await service.authorise_reports(user, report_references(result.turns))
    fence.assert_live()
    await service.commit()
    await service.authorise_reports(user, report_references(result.turns))
    await fence.confirm()
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> SavedConversationOut:
    service = container.assistant_history(session)
    record = await service.get(user, conversation_id)
    await fence.confirm()
    result = conversation_out(record)
    await service.authorise_reports(user, report_references(result.turns))
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.put("/{conversation_id}")
async def replace_conversation(
    conversation_id: UUID,
    body: SavedConversationIn,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> SavedConversationOut:
    await fence.confirm()
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
    fence.assert_live()
    await service.commit()
    await service.authorise_reports(user, report_references(result.turns))
    await fence.confirm()
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
) -> Response:
    await fence.confirm()
    service = container.assistant_history(session)
    await service.remove(user, conversation_id)
    fence.assert_live()
    await service.commit()
    await fence.confirm()
    fence.assert_live()
    return Response(status_code=204, headers={"Cache-Control": "private, no-store"})
