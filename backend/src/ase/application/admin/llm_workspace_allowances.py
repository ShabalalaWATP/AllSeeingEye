"""Daily preset updates which preserve other periods and temporary overrides."""

from ase.application.admin.llm_workspace_inputs import PRESET_LIMITS, WorkspaceChange
from ase.application.ai_usage_admin import AiPolicyInput, AiUsagePolicyAdmin
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock
from ase.application.ports.ai_usage import AiUsageRepository
from ase.domain.ai_usage import AiAllowancePeriod, AiPolicyScope
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRequest
from ase.domain.users import User


class WorkspaceAllowances:
    def __init__(self, repository: AiUsageRepository, clock: Clock, auditor: Auditor) -> None:
        self.repository, self.clock, self.auditor = repository, clock, auditor
        self.admin = AiUsagePolicyAdmin(repository, clock)

    async def lock(self, changes: list[WorkspaceChange]) -> None:
        targets = {(change.scope, change.target_id) for change in changes if change.allowance}
        policies = [
            policy
            for policy in await self.repository.list_policies()
            if policy.enabled
            and policy.period is AiAllowancePeriod.DAY
            and (policy.scope, policy.target_id) in targets
        ]
        # Match the admission ledger's lock order to avoid cross-policy deadlocks.
        for policy in sorted(policies, key=lambda item: item.id):
            await self.repository.lock_policy(policy.id)

    async def apply(self, actor: User, change: WorkspaceChange, context: RequestContext) -> None:
        data = change.allowance
        if data is None:
            return
        scope = AiPolicyScope(change.scope)
        current = await self.repository.find_policy(scope, change.target_id, AiAllowancePeriod.DAY)
        if (current.id if current else None) != data.expected_policy_id or (
            current.revision if current else None
        ) != data.expected_policy_revision:
            raise InvalidRequest("This daily allowance changed. Reload before applying it.")
        if current and await self.repository.count_open_overrides(current.id, self.clock.now()):
            raise InvalidRequest(
                "Resolve this daily allowance's temporary overrides "
                "in advanced usage controls first."
            )
        if data.preset == "inherit":
            if current is None:
                return
            await self.admin.disable(actor, current.id)
            action = AuditAction.AI_USAGE_POLICY_DISABLED
            policy_id = current.id
        else:
            requests, tokens = PRESET_LIMITS[data.preset]
            policy_input = AiPolicyInput(
                scope, change.target_id, AiAllowancePeriod.DAY, requests, tokens, True
            )
            if current:
                updated = await self.admin.update(actor, current.id, policy_input)
                action = AuditAction.AI_USAGE_POLICY_UPDATED
            else:
                updated = await self.admin.create(actor, policy_input)
                action = AuditAction.AI_USAGE_POLICY_CREATED
            policy_id = updated.id
        await self.auditor.record(
            action,
            actor=actor.id,
            subject=str(policy_id),
            ip=context.ip,
            details={"scope": change.scope, "preset": data.preset, "period": "day"},
        )
