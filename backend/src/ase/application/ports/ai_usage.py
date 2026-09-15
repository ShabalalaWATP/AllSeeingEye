"""Persistence port for administrator controlled AI admission accounting."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.ai_usage import (
    AiPolicyScope,
    AiUsagePolicy,
    AiUsageReservation,
    AiUsageSummary,
)


class AiUsageRepository(Protocol):
    async def get_policy(self, policy_id: UUID) -> AiUsagePolicy | None: ...

    async def find_policy(
        self, scope: AiPolicyScope, target_id: UUID | None
    ) -> AiUsagePolicy | None: ...

    async def list_policies(self, scope: AiPolicyScope | None = None) -> list[AiUsagePolicy]: ...

    async def add_policy(self, policy: AiUsagePolicy) -> None: ...

    async def save_policy(self, policy: AiUsagePolicy) -> None: ...

    async def effective_policies(
        self, user_id: UUID, *, team_id: UUID | None = None
    ) -> list[AiUsagePolicy]: ...

    async def reserve(
        self,
        policy_id: UUID,
        *,
        user_id: UUID,
        profile_id: UUID | None,
        model: str,
        purpose: str,
        requested_tokens: int,
        now: datetime,
    ) -> AiUsageReservation: ...

    async def settle(
        self,
        reservation_id: UUID,
        *,
        ok: bool,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        error: str | None,
        now: datetime,
    ) -> AiUsageReservation: ...

    async def summary(
        self, user_id: UUID, *, now: datetime, team_id: UUID | None = None
    ) -> list[AiUsageSummary]: ...

    async def list_reservations(self, limit: int = 100) -> list[AiUsageReservation]: ...
