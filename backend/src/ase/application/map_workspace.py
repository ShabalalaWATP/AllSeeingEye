"""Personal/team workspace operations with fresh session checks and bounded retention."""

from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.map_workspace import MapWorkspaceRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.map_workspace import (
    MAX_SCOPE_DOCUMENTS,
    MapWorkspaceDocument,
    WorkspaceKind,
    validate_payload,
)


class MapWorkspace:
    def __init__(
        self,
        users: UserRepository,
        refresh: RefreshTokenRepository,
        documents: MapWorkspaceRepository,
        access: AccessPolicy,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self.users, self.refresh, self.documents = users, refresh, documents
        self.access, self.clock, self.auditor, self.uow = access, clock, auditor, uow

    async def _context(self, claims: AccessClaims) -> AccessContext:
        await self.users.lock_administration()
        await self.users.lock_by_id(claims.user_id)
        actor = await validate_current_session(claims, self.users, self.refresh, self.clock)
        return await self.access.context(actor)

    async def _get(self, access: AccessContext, document_id: UUID) -> MapWorkspaceDocument:
        document = await self.documents.get(document_id)
        if document is None:
            raise NotFound()
        access.require_read(document.created_by, document.team_id)
        return document

    def _validate(self, kind: WorkspaceKind, title: str, payload: dict[str, Any]) -> str:
        if not title.strip() or len(title) > 200:
            raise InvalidRequest("A map document needs a title of up to 200 characters.")
        try:
            validate_payload(kind, payload)
        except (ValueError, TypeError, OverflowError) as exc:
            raise InvalidRequest(str(exc)) from exc
        return title.strip()

    async def list(
        self, claims: AccessClaims, kind: WorkspaceKind, limit: int = 100, offset: int = 0
    ) -> list[MapWorkspaceDocument]:
        if kind not in ("drawings", "radio") or not 1 <= limit <= 100 or not 0 <= offset <= 10000:
            raise InvalidRequest("Invalid map document page.")
        access = await self._context(claims)
        documents = await self.documents.list_visible(access.visibility, kind, limit, offset)
        await self.uow.commit()
        return documents

    async def get(self, claims: AccessClaims, document_id: UUID) -> MapWorkspaceDocument:
        document = await self._get(await self._context(claims), document_id)
        await self.uow.commit()
        return document

    async def create(
        self,
        claims: AccessClaims,
        kind: WorkspaceKind,
        title: str,
        payload: dict[str, Any],
        team_id: UUID | None,
        context: RequestContext,
    ) -> MapWorkspaceDocument:
        title = self._validate(kind, title, payload)
        access = await self._context(claims)
        access.require_create(team_id)
        if await self.documents.scope_count(access.actor.id, team_id) >= MAX_SCOPE_DOCUMENTS:
            raise InvalidRequest("This personal/team scope has reached its 100 map document limit.")
        now = self.clock.now()
        document = MapWorkspaceDocument(
            uuid4(), kind, title, payload, 1, access.actor.id, team_id, now, now
        )
        await self.documents.create(document)
        await self._audit(access, document, "create", context)
        await self.uow.commit()
        return document

    async def update(
        self,
        claims: AccessClaims,
        document_id: UUID,
        title: str,
        payload: dict[str, Any],
        expected_revision: int,
        context: RequestContext,
    ) -> MapWorkspaceDocument:
        access = await self._context(claims)
        document = await self._get(access, document_id)
        access.require_write(document.created_by, document.team_id)
        title = self._validate(document.kind, title, payload)
        if document.revision != expected_revision or type(expected_revision) is not int:
            raise Conflict()
        revised = replace(
            document,
            title=title,
            payload=payload,
            revision=document.revision + 1,
            updated_at=self.clock.now(),
        )
        if not await self.documents.update(revised, expected_revision):
            await self.uow.rollback()
            raise Conflict()
        await self._audit(access, revised, "update", context)
        await self.uow.commit()
        return revised

    async def remove(
        self, claims: AccessClaims, document_id: UUID, context: RequestContext
    ) -> None:
        access = await self._context(claims)
        document = await self._get(access, document_id)
        access.require_write(document.created_by, document.team_id)
        await self.documents.remove(document.id)
        await self._audit(access, document, "delete", context)
        await self.uow.commit()

    async def _audit(
        self,
        access: AccessContext,
        document: MapWorkspaceDocument,
        operation: str,
        context: RequestContext,
    ) -> None:
        await self.auditor.record(
            AuditAction.MAP_WORKSPACE_CHANGED,
            actor=access.actor.id,
            subject=str(document.id),
            ip=context.ip,
            details={"operation": operation, "kind": document.kind, "revision": document.revision},
        )
