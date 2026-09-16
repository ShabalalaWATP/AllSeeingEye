"""SQL storage for AI allowance policies, dated overrides and their current summaries."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update

from ase.adapters.persistence.ai_usage_mapping import (
    override_from_row,
    policy_from_row,
    rowcount,
)
from ase.adapters.persistence.ai_usage_models import (
    AiUsageCounterRow,
    AiUsagePolicyOverrideRow,
    AiUsagePolicyRow,
)
from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.teams import TeamMembershipRow
from ase.domain.ai_usage import (
    AiAllowancePeriod,
    AiAttribution,
    AiPolicyScope,
    AiUsagePolicy,
    AiUsageSummary,
    period_bounds,
)
from ase.domain.ai_usage_overrides import AiPolicyOverride
from ase.domain.errors import NotFound

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SqlAiPolicyStore:
    """Policy and override persistence. Callers own the transaction boundary."""

    if TYPE_CHECKING:
        _session: AsyncSession

    async def get_policy(self, policy_id: UUID) -> AiUsagePolicy | None:
        row = await self._session.get(AiUsagePolicyRow, policy_id, populate_existing=True)
        return policy_from_row(row) if row else None

    async def find_policy(
        self, scope: AiPolicyScope, target_id: UUID | None, period: AiAllowancePeriod
    ) -> AiUsagePolicy | None:
        """One enabled policy per scope, target and period, matching the unique index."""
        row = await self._session.scalar(
            select(AiUsagePolicyRow)
            .where(
                AiUsagePolicyRow.scope == scope.value,
                AiUsagePolicyRow.target_id == target_id
                if target_id is not None
                else AiUsagePolicyRow.target_id.is_(None),
                AiUsagePolicyRow.period == period.value,
                AiUsagePolicyRow.enabled,
            )
            .order_by(AiUsagePolicyRow.revision.desc())
        )
        return policy_from_row(row) if row else None

    async def list_policies(self, scope: AiPolicyScope | None = None) -> list[AiUsagePolicy]:
        statement = select(AiUsagePolicyRow)
        if scope is not None:
            statement = statement.where(AiUsagePolicyRow.scope == scope.value)
        rows = await self._session.scalars(
            statement.order_by(AiUsagePolicyRow.scope, AiUsagePolicyRow.target_id)
        )
        return [policy_from_row(row) for row in rows]

    async def add_policy(self, policy: AiUsagePolicy) -> None:
        self._session.add(
            AiUsagePolicyRow(
                id=policy.id,
                scope=policy.scope.value,
                target_id=policy.target_id,
                period=policy.period.value,
                request_limit=policy.request_limit,
                token_limit=policy.token_limit,
                enabled=policy.enabled,
                revision=policy.revision,
                created_at=policy.created_at,
                updated_at=policy.updated_at,
            )
        )
        await self._session.flush()

    async def save_policy(self, policy: AiUsagePolicy) -> None:
        row = await self._session.get(AiUsagePolicyRow, policy.id)
        if row is None:
            raise NotFound()
        row.scope = policy.scope.value
        row.target_id = policy.target_id
        row.period = policy.period.value
        row.request_limit = policy.request_limit
        row.token_limit = policy.token_limit
        row.enabled = policy.enabled
        row.revision = policy.revision
        row.created_at = policy.created_at
        row.updated_at = policy.updated_at
        await self._session.flush()

    async def lock_policy(self, policy_id: UUID) -> bool:
        """A no-op update serialises policy edits with admission for the same policy."""
        result = await self._session.execute(
            update(AiUsagePolicyRow)
            .where(AiUsagePolicyRow.id == policy_id)
            .values(updated_at=AiUsagePolicyRow.updated_at)
        )
        return rowcount(result) == 1

    async def can_attribute_to_team(self, user_id: UUID, team_id: UUID) -> bool:
        """A team allowance is charged for current members or active site administrators."""
        member = await self._session.scalar(
            select(TeamMembershipRow.user_id).where(
                TeamMembershipRow.team_id == team_id, TeamMembershipRow.user_id == user_id
            )
        )
        if member is not None:
            return True
        admin = await self._session.scalar(
            select(UserRow.id).where(
                UserRow.id == user_id, UserRow.role == "admin", UserRow.is_active
            )
        )
        return admin is not None

    async def effective_policies(self, attribution: AiAttribution) -> list[AiUsagePolicy]:
        """Enabled policies for an already validated attribution, in lock order."""
        return await self.view_policies(
            user_id=attribution.user_id,
            team_id=attribution.team_id,
            system=attribution.system,
        )

    async def view_policies(
        self, *, user_id: UUID | None, team_id: UUID | None, system: bool = False
    ) -> list[AiUsagePolicy]:
        """Enabled policies for the given dimensions; the caller authorises the view."""
        predicates = [AiUsagePolicyRow.scope == AiPolicyScope.GLOBAL.value]
        if system:
            predicates.append(AiUsagePolicyRow.scope == AiPolicyScope.SYSTEM.value)
        if user_id is not None:
            predicates.append(
                and_(
                    AiUsagePolicyRow.scope == AiPolicyScope.USER.value,
                    AiUsagePolicyRow.target_id == user_id,
                )
            )
        if team_id is not None:
            predicates.append(
                and_(
                    AiUsagePolicyRow.scope == AiPolicyScope.TEAM.value,
                    AiUsagePolicyRow.target_id == team_id,
                )
            )
        rows = await self._session.scalars(
            select(AiUsagePolicyRow)
            .where(AiUsagePolicyRow.enabled, or_(*predicates))
            .order_by(AiUsagePolicyRow.id)
        )
        return [policy_from_row(row) for row in rows]

    async def active_override(self, policy_id: UUID, now: datetime) -> AiPolicyOverride | None:
        row = await self._session.scalar(
            select(AiUsagePolicyOverrideRow)
            .where(
                AiUsagePolicyOverrideRow.policy_id == policy_id,
                AiUsagePolicyOverrideRow.revoked_at.is_(None),
                AiUsagePolicyOverrideRow.effective_from <= now,
                AiUsagePolicyOverrideRow.expires_at > now,
            )
            .order_by(
                AiUsagePolicyOverrideRow.created_at.desc(), AiUsagePolicyOverrideRow.id.desc()
            )
            .limit(1)
        )
        return override_from_row(row) if row else None

    async def list_overrides(self, policy_id: UUID, limit: int = 50) -> list[AiPolicyOverride]:
        rows = await self._session.scalars(
            select(AiUsagePolicyOverrideRow)
            .where(AiUsagePolicyOverrideRow.policy_id == policy_id)
            .order_by(AiUsagePolicyOverrideRow.created_at.desc())
            .limit(limit)
        )
        return [override_from_row(row) for row in rows]

    async def count_open_overrides(self, policy_id: UUID, now: datetime) -> int:
        return int(
            await self._session.scalar(
                select(func.count())
                .select_from(AiUsagePolicyOverrideRow)
                .where(
                    AiUsagePolicyOverrideRow.policy_id == policy_id,
                    AiUsagePolicyOverrideRow.revoked_at.is_(None),
                    AiUsagePolicyOverrideRow.expires_at > now,
                )
            )
            or 0
        )

    async def get_override(self, override_id: UUID) -> AiPolicyOverride | None:
        row = await self._session.get(AiUsagePolicyOverrideRow, override_id, populate_existing=True)
        return override_from_row(row) if row else None

    async def add_override(self, override: AiPolicyOverride) -> None:
        self._session.add(
            AiUsagePolicyOverrideRow(
                id=override.id,
                policy_id=override.policy_id,
                request_state=override.requests.state.value,
                request_limit=override.requests.value,
                token_state=override.tokens.state.value,
                token_limit=override.tokens.value,
                effective_from=override.effective_from,
                expires_at=override.expires_at,
                created_by=override.created_by,
                created_at=override.created_at,
                revoked_at=override.revoked_at,
            )
        )
        await self._session.flush()

    async def revoke_override(self, override_id: UUID, now: datetime) -> bool:
        result = await self._session.execute(
            update(AiUsagePolicyOverrideRow)
            .where(
                AiUsagePolicyOverrideRow.id == override_id,
                AiUsagePolicyOverrideRow.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        return rowcount(result) == 1

    async def summaries_for(
        self, policies: list[AiUsagePolicy], now: datetime
    ) -> list[AiUsageSummary]:
        result: list[AiUsageSummary] = []
        for policy in policies:
            start, end = period_bounds(now, policy.period)
            counter = await self._session.get(
                AiUsageCounterRow, (policy.id, start), populate_existing=True
            )
            result.append(
                AiUsageSummary(
                    policy,
                    start,
                    end,
                    counter.used_requests if counter else 0,
                    counter.reserved_requests if counter else 0,
                    counter.used_tokens if counter else 0,
                    counter.reserved_tokens if counter else 0,
                    await self.active_override(policy.id, now),
                )
            )
        return result
