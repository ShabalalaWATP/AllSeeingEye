"""Persistence port for administrator controlled AI admission accounting."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.ai_usage import (
    AiAttribution,
    AiCallOutcome,
    AiMemberUsage,
    AiPolicyScope,
    AiReservationStatus,
    AiUsagePolicy,
    AiUsageReservation,
    AiUsageSummary,
    AiUsageTotals,
)
from ase.domain.ai_usage_overrides import AiPolicyOverride


class AiPolicyRepository(Protocol):
    async def get_policy(self, policy_id: UUID) -> AiUsagePolicy | None: ...

    async def find_policy(
        self, scope: AiPolicyScope, target_id: UUID | None
    ) -> AiUsagePolicy | None: ...

    async def list_policies(self, scope: AiPolicyScope | None = None) -> list[AiUsagePolicy]: ...

    async def add_policy(self, policy: AiUsagePolicy) -> None: ...

    async def save_policy(self, policy: AiUsagePolicy) -> None: ...

    async def lock_policy(self, policy_id: UUID) -> bool: ...

    async def can_attribute_to_team(self, user_id: UUID, team_id: UUID) -> bool: ...

    async def effective_policies(self, attribution: AiAttribution) -> list[AiUsagePolicy]: ...

    async def view_policies(
        self, *, user_id: UUID | None, team_id: UUID | None, system: bool = False
    ) -> list[AiUsagePolicy]: ...

    async def summaries_for(
        self, policies: list[AiUsagePolicy], now: datetime
    ) -> list[AiUsageSummary]: ...

    async def active_override(self, policy_id: UUID, now: datetime) -> AiPolicyOverride | None: ...

    async def list_overrides(self, policy_id: UUID, limit: int = 50) -> list[AiPolicyOverride]: ...

    async def count_open_overrides(self, policy_id: UUID, now: datetime) -> int: ...

    async def get_override(self, override_id: UUID) -> AiPolicyOverride | None: ...

    async def add_override(self, override: AiPolicyOverride) -> None: ...

    async def revoke_override(self, override_id: UUID, now: datetime) -> bool: ...


class AiLedgerRepository(Protocol):
    async def reserve(
        self,
        policy_id: UUID,
        *,
        call_id: UUID,
        attribution: AiAttribution,
        profile_id: UUID | None,
        model: str,
        purpose: str,
        requested_tokens: int,
        now: datetime,
    ) -> AiUsageReservation: ...

    async def mark_dispatched(self, call_id: UUID, now: datetime) -> None: ...

    async def finish(
        self,
        call_id: UUID,
        *,
        outcome: AiCallOutcome,
        attribution: AiAttribution,
        reserved_at: datetime,
        requested_tokens: int,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        error: str | None,
        now: datetime,
    ) -> None: ...

    async def stale_reservations(
        self, before: datetime, limit: int
    ) -> list[AiUsageReservation]: ...

    async def count_reservations(self, status: AiReservationStatus) -> int: ...

    async def list_reservations(self, limit: int = 100) -> list[AiUsageReservation]: ...

    async def account_totals(self, user_id: UUID, now: datetime) -> AiUsageTotals: ...

    async def team_totals(
        self, team_id: UUID, now: datetime, *, user_id: UUID | None = None
    ) -> AiUsageTotals: ...

    async def system_totals(self, now: datetime) -> AiUsageTotals: ...

    async def team_member_totals(self, team_id: UUID, now: datetime) -> list[AiMemberUsage]: ...


class AiUsagePruningRepository(Protocol):
    """Bounded deletion of expired ledger rows; each call removes at most ``limit`` rows."""

    async def prune_reservations(self, before: datetime, limit: int) -> int: ...

    async def prune_counters(self, before: datetime, limit: int) -> int: ...

    async def prune_totals(self, before: datetime, limit: int) -> int: ...


class AiUsageRepository(AiPolicyRepository, AiLedgerRepository, AiUsagePruningRepository, Protocol):
    """The combined repository the container binds for each session."""
