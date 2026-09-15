"""Administrator-only AI allowance policies and dated temporary overrides."""

from __future__ import annotations

import builtins
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from ase.application.policy import require_admin
from ase.application.ports.ai_usage import AiUsageRepository
from ase.domain.ai_usage import AiAllowancePeriod, AiPolicyScope, AiUsagePolicy
from ase.domain.ai_usage_overrides import MAX_OPEN_OVERRIDES, AiLimitOverride, AiPolicyOverride
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.users import User

if TYPE_CHECKING:
    from ase.application.ports import Clock


@dataclass(frozen=True, slots=True)
class AiPolicyInput:
    scope: AiPolicyScope
    target_id: UUID | None
    period: AiAllowancePeriod
    request_limit: int | None
    token_limit: int | None
    enabled: bool


@dataclass(frozen=True, slots=True)
class AiOverrideInput:
    requests: AiLimitOverride
    tokens: AiLimitOverride
    effective_from: datetime
    expires_at: datetime


class AiUsagePolicyAdmin:
    """Admin-only CRUD; policy edits become effective on the next admission decision."""

    def __init__(self, repository: AiUsageRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def list(self, actor: User) -> list[AiUsagePolicy]:
        require_admin(actor)
        return await self._repository.list_policies()

    async def create(self, actor: User, data: AiPolicyInput) -> AiUsagePolicy:
        require_admin(actor)
        if data.enabled and await self._repository.find_policy(data.scope, data.target_id):
            raise Conflict("An AI policy already exists for this target.")
        now = self._clock.now()
        policy = AiUsagePolicy(
            uuid4(),
            data.scope,
            data.target_id,
            data.period,
            data.request_limit,
            data.token_limit,
            data.enabled,
            1,
            now,
            now,
        )
        await self._repository.add_policy(policy)
        return policy

    async def update(self, actor: User, policy_id: UUID, data: AiPolicyInput) -> AiUsagePolicy:
        require_admin(actor)
        current = await self._repository.get_policy(policy_id)
        if current is None:
            raise NotFound()
        existing = await self._repository.find_policy(data.scope, data.target_id)
        if data.enabled and existing is not None and existing.id != current.id:
            raise Conflict("An AI policy already exists for this target.")
        await self._repository.lock_policy(policy_id)
        updated = AiUsagePolicy(
            current.id,
            data.scope,
            data.target_id,
            data.period,
            data.request_limit,
            data.token_limit,
            data.enabled,
            current.revision + 1,
            current.created_at,
            self._clock.now(),
        )
        await self._repository.save_policy(updated)
        return updated

    async def disable(self, actor: User, policy_id: UUID) -> None:
        require_admin(actor)
        current = await self._repository.get_policy(policy_id)
        if current is None:
            raise NotFound()
        await self.update(
            actor,
            policy_id,
            AiPolicyInput(
                current.scope,
                current.target_id,
                current.period,
                current.request_limit,
                current.token_limit,
                False,
            ),
        )

    async def list_overrides(self, actor: User, policy_id: UUID) -> builtins.list[AiPolicyOverride]:
        require_admin(actor)
        if await self._repository.get_policy(policy_id) is None:
            raise NotFound()
        return await self._repository.list_overrides(policy_id)

    async def create_override(
        self, actor: User, policy_id: UUID, data: AiOverrideInput
    ) -> AiPolicyOverride:
        require_admin(actor)
        now = self._clock.now()
        # Serialise with admission and other override edits for this policy.
        if not await self._repository.lock_policy(policy_id):
            raise NotFound()
        if data.expires_at <= now:
            raise InvalidRequest("A temporary override must expire in the future.")
        if await self._repository.count_open_overrides(policy_id, now) >= MAX_OPEN_OVERRIDES:
            raise Conflict("This policy already has the maximum number of open overrides.")
        override = AiPolicyOverride(
            uuid4(),
            policy_id,
            data.requests,
            data.tokens,
            data.effective_from,
            data.expires_at,
            actor.id,
            now,
        )
        await self._repository.add_override(override)
        return override

    async def revoke_override(self, actor: User, override_id: UUID) -> AiPolicyOverride:
        require_admin(actor)
        current = await self._repository.get_override(override_id)
        if current is None:
            raise NotFound()
        await self._repository.lock_policy(current.policy_id)
        await self._repository.revoke_override(override_id, self._clock.now())
        revoked = await self._repository.get_override(override_id)
        if revoked is None:
            raise NotFound()
        return revoked
