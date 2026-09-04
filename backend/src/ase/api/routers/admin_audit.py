"""Audit log (admin only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from ase.api.deps import AdminUser, ContainerDep, SessionDep
from ase.api.schemas import AuditEntryOut, AuditPageOut

router = APIRouter(prefix="/admin/audit-log", tags=["admin"])


@router.get("")
async def list_audit(
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    before: Annotated[int | None, Query(ge=1)] = None,
) -> AuditPageOut:
    page = await container.list_audit(session).execute(admin, before, limit)
    return AuditPageOut(
        items=[AuditEntryOut.from_entity(item) for item in page.items],
        next_before=page.next_before,
    )
