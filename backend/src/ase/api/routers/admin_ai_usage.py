"""Administrator configuration and audit views for AI allowances."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import AdminUser, ContainerDep, ContextDep, SessionDep
from ase.api.schemas_ai_defaults import AiPolicyDefaultsOut, AppliedDefaultsOut
from ase.api.schemas_ai_usage import (
    AiUsagePolicyIn,
    AiUsagePolicyOut,
    AiUsagePreviewOut,
    AiUsageReservationOut,
    AiUsageReservationsOut,
)
from ase.api.schemas_ai_usage_overrides import (
    AiPolicyOverrideIn,
    AiPolicyOverrideOut,
    AiPolicyOverridesOut,
)
from ase.application.ai_usage_admin import AiUsagePolicyAdmin
from ase.application.ai_usage_defaults import AiUsageDefaults
from ase.application.auditing import Auditor
from ase.domain.ai_usage import AiUsagePolicy
from ase.domain.ai_usage_overrides import AiPolicyOverride
from ase.domain.audit import AuditAction

router = APIRouter(prefix="/admin/ai-usage", tags=["admin"])


def _service(session: SessionDep, container: ContainerDep) -> AiUsagePolicyAdmin:
    return AiUsagePolicyAdmin(container.repositories(session).ai_usage, container.clock)


def _defaults(session: SessionDep, container: ContainerDep) -> AiUsageDefaults:
    repos = container.repositories(session)
    return AiUsageDefaults(
        repos.ai_usage, repos.users, _service(session, container), container.clock
    )


async def _audit(
    session: SessionDep,
    container: ContainerDep,
    action: AuditAction,
    *,
    actor: UUID,
    subject: str,
    ip: str | None,
    details: dict[str, Any] | None = None,
) -> None:
    auditor = Auditor(container.repositories(session).audit, container.clock)
    await auditor.record(action, actor=actor, subject=subject, ip=ip, details=details)
    await container.repositories(session).uow.commit()


def _policy_details(policy: AiUsagePolicy) -> dict[str, Any]:
    return {
        "scope": policy.scope.value,
        "target_id": str(policy.target_id) if policy.target_id else None,
        "period": policy.period.value,
        "request_limit": policy.request_limit,
        "token_limit": policy.token_limit,
        "enabled": policy.enabled,
        "revision": policy.revision,
    }


def _override_details(override: AiPolicyOverride) -> dict[str, Any]:
    return {
        "policy_id": str(override.policy_id),
        "requests": override.requests.state.value,
        "request_limit": override.requests.value,
        "tokens": override.tokens.state.value,
        "token_limit": override.tokens.value,
        "effective_from": override.effective_from.isoformat(),
        "expires_at": override.expires_at.isoformat(),
    }


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
    await _audit(
        session,
        container,
        AuditAction.AI_USAGE_POLICY_CREATED,
        actor=admin.id,
        subject=str(policy.id),
        ip=context.ip,
        details=_policy_details(policy),
    )
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
    await _audit(
        session,
        container,
        AuditAction.AI_USAGE_POLICY_UPDATED,
        actor=admin.id,
        subject=str(policy.id),
        ip=context.ip,
        details=_policy_details(policy),
    )
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
    await _audit(
        session,
        container,
        AuditAction.AI_USAGE_POLICY_DISABLED,
        actor=admin.id,
        subject=str(policy_id),
        ip=context.ip,
    )
    return Response(status_code=204)


@router.get("/policies/{policy_id}/overrides")
async def list_overrides(
    policy_id: UUID, admin: AdminUser, session: SessionDep, container: ContainerDep
) -> AiPolicyOverridesOut:
    items = await _service(session, container).list_overrides(admin, policy_id)
    return AiPolicyOverridesOut(items=[AiPolicyOverrideOut.from_override(item) for item in items])


@router.post("/policies/{policy_id}/overrides", status_code=201)
async def create_override(
    policy_id: UUID,
    body: AiPolicyOverrideIn,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> AiPolicyOverrideOut:
    override = await _service(session, container).create_override(admin, policy_id, body.to_input())
    await _audit(
        session,
        container,
        AuditAction.AI_USAGE_OVERRIDE_CREATED,
        actor=admin.id,
        subject=str(override.id),
        ip=context.ip,
        details=_override_details(override),
    )
    return AiPolicyOverrideOut.from_override(override)


@router.delete("/overrides/{override_id}")
async def revoke_override(
    override_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> AiPolicyOverrideOut:
    override = await _service(session, container).revoke_override(admin, override_id)
    await _audit(
        session,
        container,
        AuditAction.AI_USAGE_OVERRIDE_REVOKED,
        actor=admin.id,
        subject=str(override.id),
        ip=context.ip,
        details={"policy_id": str(override.policy_id)},
    )
    return AiPolicyOverrideOut.from_override(override)


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


@router.get("/preview", response_model=AiUsagePreviewOut)
async def preview_effective_usage(
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    user_id: UUID | None = None,
    team_id: UUID | None = None,
    system: bool = False,
) -> AiUsagePreviewOut:
    """Show the policies a call would be charged to, for an account or system work."""
    preview = await container.ai_usage_views(session).preview(
        admin, user_id=user_id, team_id=team_id, system=system
    )
    return AiUsagePreviewOut.from_preview(preview, container.settings.ai_token_prices)


@router.get("/defaults", response_model=AiPolicyDefaultsOut)
async def preview_default_policies(
    admin: AdminUser, session: SessionDep, container: ContainerDep
) -> AiPolicyDefaultsOut:
    """The documented starting set, beside the usage it is compared against."""
    defaults = await _defaults(session, container).preview(admin)
    return AiPolicyDefaultsOut.from_defaults(defaults, container.settings.ai_token_prices)


@router.post("/defaults", status_code=201)
async def apply_default_policies(
    admin: AdminUser, session: SessionDep, container: ContainerDep, context: ContextDep
) -> AppliedDefaultsOut:
    """Create every missing policy in the set. Existing policies are never overwritten."""
    created = await _defaults(session, container).apply(admin)
    await _audit(
        session,
        container,
        AuditAction.AI_USAGE_DEFAULTS_APPLIED,
        actor=admin.id,
        subject=str(admin.id),
        ip=context.ip,
        details={
            "created": len(created),
            "policies": [_policy_details(policy) for policy in created[:50]],
        },
    )
    return AppliedDefaultsOut.from_policies(created)
