"""Preview and deliberately apply the documented starting set of AI allowance policies.

Applying is explicit: an administrator sees exactly what would be created, including the
measured usage the suggestion is compared against, and only a separate call writes it.
A scope, target and period that already carries an enabled policy is never overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from ase.application.ai_usage_admin import AiPolicyInput, AiUsagePolicyAdmin
from ase.application.policy import require_admin
from ase.application.ports.ai_usage import AiUsageRepository
from ase.application.ports.repositories import UserRepository
from ase.domain.ai_defaults import DEFAULT_POLICY_SET, AiDefaultPolicy
from ase.domain.ai_usage import (
    AiAllowancePeriod,
    AiPolicyScope,
    AiUsagePolicy,
    AiUsageTotals,
    period_bounds,
)
from ase.domain.users import User

if TYPE_CHECKING:
    from ase.application.ports import Clock

# Days in the observed month so far, used only to describe the suggestion's headroom.
MIN_OBSERVED_DAYS = 1


@dataclass(frozen=True, slots=True)
class SuggestedPolicy:
    """One policy the set would create, and whether an enabled one already exists."""

    scope: AiPolicyScope
    target_id: UUID | None
    target_name: str
    period: AiAllowancePeriod
    token_limit: int
    reason: str
    already_configured: bool


@dataclass(frozen=True, slots=True)
class AiPolicyDefaults:
    items: list[SuggestedPolicy]
    observed: AiUsageTotals
    observed_daily_tokens: int
    any_policy_configured: bool


class AiUsageDefaults:
    """Administrator-only. Reads are safe; applying writes only missing policies."""

    def __init__(
        self,
        repository: AiUsageRepository,
        users: UserRepository,
        admin: AiUsagePolicyAdmin,
        clock: Clock,
    ) -> None:
        self._repository, self._users = repository, users
        self._admin, self._clock = admin, clock

    async def preview(self, actor: User) -> AiPolicyDefaults:
        require_admin(actor)
        now = self._clock.now()
        observed = await self._repository.site_totals(now)
        start, _ = period_bounds(now, AiAllowancePeriod.MONTH)
        days = max(MIN_OBSERVED_DAYS, (now - start).days + 1)
        items: list[SuggestedPolicy] = []
        for default in DEFAULT_POLICY_SET:
            for target_id, target_name in await self._targets(default):
                existing = await self._repository.find_policy(
                    default.scope, target_id, default.period
                )
                items.append(
                    SuggestedPolicy(
                        default.scope,
                        target_id,
                        target_name,
                        default.period,
                        default.token_limit,
                        default.reason,
                        existing is not None,
                    )
                )
        return AiPolicyDefaults(
            items,
            observed,
            observed.used_tokens // days,
            any(policy.enabled for policy in await self._repository.list_policies()),
        )

    async def apply(self, actor: User) -> list[AiUsagePolicy]:
        """Create every missing policy in the set; leave every existing one untouched."""
        require_admin(actor)
        created: list[AiUsagePolicy] = []
        for suggestion in (await self.preview(actor)).items:
            if suggestion.already_configured:
                continue
            created.append(
                await self._admin.create(
                    actor,
                    AiPolicyInput(
                        suggestion.scope,
                        suggestion.target_id,
                        suggestion.period,
                        None,
                        suggestion.token_limit,
                        True,
                    ),
                )
            )
        return created

    async def _targets(self, default: AiDefaultPolicy) -> list[tuple[UUID | None, str]]:
        if not default.per_active_user:
            return [(None, "Everyone" if default.scope is AiPolicyScope.GLOBAL else "System work")]
        return [
            (user.id, user.display_name) for user in await self._users.list_all() if user.is_active
        ]
