"""Administrator configuration and audit views for AI allowances."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.adapters.persistence.teams import SqlTeamRepository
from ase.api.deps import AdminUser, ContainerDep, ContextDep, SessionDep
from ase.api.schemas_ai_usage import (
    AiUsagePolicyIn,
    AiUsagePolicyOut,
    AiUsageReservationOut,
    AiUsageReservationsOut,
    AiUsageSummaryOut,
    AiUsageSummaryPageOut,
)
from ase.application.ai_usage import AiUsagePolicyAdmin
from ase.application.auditing import Auditor
from ase.domain.audit import AuditAction
from ase.domain.errors import NotFound

router = APIRouter(prefix="/admin/ai-usage", tags=["admin"])


def _service(session: SessionDep, container: ContainerDep) -> AiUsagePolicyAdmin:
    return AiUsagePolicyAdmin(container.repositories(session).ai_usage, container.clock)


def _audit(session: SessionDep, container: ContainerDep) -> Auditor:
    return Auditor(container.repositories(session).audit, container.clock)


@router.get("/policies")
async def list_policies(
    admin: AdminUser, session: SessionDep, container: ContainerDep
) -> list[AiUsagePolicyOut]:
    policies = await _service(session, container).list(admin)
    return [AiUsagePolicyOut.from_policy(policy) for policy in policies]


@router.post("/policies", status_code=201)
async def create_policy(
    body: AiUsagePolicyIn,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> AiUsagePolicyOut:
    policy = await _service(session, container).create(admin, body.to_input())
    await _audit(session, container).record(
        AuditAction.AI_USAGE_POLICY_CREATED,
        actor=admin.id,
        subject=str(policy.id),
        ip=context.ip,
        details={
            "scope": policy.scope.value,
            "target_id": str(policy.target_id) if policy.target_id else None,
            "period": policy.period.value,
            "request_limit": policy.request_limit,
            "token_limit": policy.token_limit,
            "enabled": policy.enabled,
        },
    )
    await container.repositories(session).uow.commit()
    return AiUsagePolicyOut.from_policy(policy)


@router.put("/policies/{policy_id}")
async def update_policy(
    policy_id: UUID,
    body: AiUsagePolicyIn,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> AiUsagePolicyOut:
    policy = await _service(session, container).update(admin, policy_id, body.to_input())
    await _audit(session, container).record(
        AuditAction.AI_USAGE_POLICY_UPDATED,
        actor=admin.id,
        subject=str(policy.id),
        ip=context.ip,
        details={
            "scope": policy.scope.value,
            "target_id": str(policy.target_id) if policy.target_id else None,
            "period": policy.period.value,
            "request_limit": policy.request_limit,
            "token_limit": policy.token_limit,
            "enabled": policy.enabled,
            "revision": policy.revision,
        },
    )
    await container.repositories(session).uow.commit()
    return AiUsagePolicyOut.from_policy(policy)


@router.delete("/policies/{policy_id}", status_code=204, response_class=Response)
async def disable_policy(
    policy_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await _service(session, container).disable(admin, policy_id)
    await _audit(session, container).record(
        AuditAction.AI_USAGE_POLICY_DISABLED,
        actor=admin.id,
        subject=str(policy_id),
        ip=context.ip,
    )
    await container.repositories(session).uow.commit()
    return Response(status_code=204)


@router.get("/reservations", response_model=AiUsageReservationsOut)
async def list_reservations(
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> AiUsageReservationsOut:
    _ = admin
    rows = await container.repositories(session).ai_usage.list_reservations(limit)
    return AiUsageReservationsOut(
        items=[AiUsageReservationOut.from_reservation(row) for row in rows]
    )


@router.get("/preview", response_model=AiUsageSummaryPageOut)
async def preview_effective_usage(
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    user_id: UUID,
    team_id: UUID | None = None,
) -> AiUsageSummaryPageOut:
    """Show the policies that would apply to a user for an optional team destination."""
    _ = admin
    target = await container.repositories(session).users.get_by_id(user_id)
    if target is None:
        raise NotFound()
    if team_id is not None:
        teams = SqlTeamRepository(session)
        team = await teams.get(team_id)
        if team is None or await teams.get_membership(team_id, user_id) is None:
            raise NotFound()
    summaries = await container.ai_usage_accounting.summaries(user_id, team_id=team_id)
    return AiUsageSummaryPageOut(items=[AiUsageSummaryOut.from_summary(item) for item in summaries])
