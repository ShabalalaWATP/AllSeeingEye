"""SQL persistence for AI policies, counters and immutable request settlements."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.ai_usage_models import (
    AiUsageCounterRow,
    AiUsagePolicyRow,
    AiUsageReservationRow,
)
from ase.adapters.persistence.teams import TeamMembershipRow
from ase.domain.ai_usage import (
    AiAllowanceExceeded,
    AiAllowancePeriod,
    AiPolicyScope,
    AiReservationStatus,
    AiUsagePolicy,
    AiUsageReservation,
    AiUsageSummary,
    period_bounds,
    token_count,
)
from ase.domain.errors import NotFound


def _rowcount(result: Any) -> int:
    """SQLAlchemy's async execute type hides rowcount although UPDATE returns it."""
    return int(cast(CursorResult[Any], result).rowcount or 0)


def _policy(row: AiUsagePolicyRow) -> AiUsagePolicy:
    return AiUsagePolicy(
        row.id,
        AiPolicyScope(row.scope),
        row.target_id,
        AiAllowancePeriod(row.period),
        row.request_limit,
        row.token_limit,
        row.enabled,
        row.revision,
        row.created_at,
        row.updated_at,
    )


def _reservation(row: AiUsageReservationRow) -> AiUsageReservation:
    return AiUsageReservation(
        row.id,
        row.policy_id,
        row.user_id,
        row.profile_id,
        row.model,
        row.purpose,
        row.period_start,
        row.period_end,
        row.reserved_tokens,
        AiReservationStatus(row.status),
        row.created_at,
        row.settled_at,
        row.prompt_tokens,
        row.completion_tokens,
        row.actual_tokens,
        row.ok,
        row.error,
    )


class SqlAiUsageRepository:
    """Policy and ledger adapter. Callers own the transaction and commit boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_policy(self, policy_id: UUID) -> AiUsagePolicy | None:
        row = await self._session.get(AiUsagePolicyRow, policy_id, populate_existing=True)
        return _policy(row) if row else None

    async def find_policy(
        self, scope: AiPolicyScope, target_id: UUID | None
    ) -> AiUsagePolicy | None:
        row = await self._session.scalar(
            select(AiUsagePolicyRow)
            .where(AiUsagePolicyRow.scope == scope.value, AiUsagePolicyRow.target_id == target_id)
            .order_by(AiUsagePolicyRow.revision.desc())
        )
        return _policy(row) if row else None

    async def list_policies(self, scope: AiPolicyScope | None = None) -> list[AiUsagePolicy]:
        statement = select(AiUsagePolicyRow)
        if scope is not None:
            statement = statement.where(AiUsagePolicyRow.scope == scope.value)
        rows = await self._session.scalars(
            statement.order_by(AiUsagePolicyRow.scope, AiUsagePolicyRow.target_id)
        )
        return [_policy(row) for row in rows]

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

    async def effective_policies(
        self, user_id: UUID, *, team_id: UUID | None = None
    ) -> list[AiUsagePolicy]:
        """Return global and user policies, plus one explicit team policy when requested.

        Personal Ask Eye calls have no team destination and therefore cannot consume a
        quota belonging to every team the account happens to join.
        """
        predicates = [
            and_(
                AiUsagePolicyRow.scope == AiPolicyScope.GLOBAL.value,
                AiUsagePolicyRow.target_id.is_(None),
            ),
            and_(
                AiUsagePolicyRow.scope == AiPolicyScope.USER.value,
                AiUsagePolicyRow.target_id == user_id,
            ),
        ]
        if team_id is not None and await self._session.scalar(
            select(TeamMembershipRow.user_id).where(
                TeamMembershipRow.team_id == team_id,
                TeamMembershipRow.user_id == user_id,
            )
        ):
            predicates.append(
                and_(
                    AiUsagePolicyRow.scope == AiPolicyScope.TEAM.value,
                    AiUsagePolicyRow.target_id == team_id,
                )
            )
        rows = await self._session.scalars(
            select(AiUsagePolicyRow)
            .where(AiUsagePolicyRow.enabled, or_(*predicates))
            .order_by(AiUsagePolicyRow.scope, AiUsagePolicyRow.target_id)
        )
        return [_policy(row) for row in rows]

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
    ) -> AiUsageReservation:
        """Atomically reserve one request and its worst-case output budget."""
        if token_count(requested_tokens) is None or requested_tokens < 1:
            raise ValueError("AI reservations need a positive bounded token amount.")
        if not 1 <= len(model) <= 2048 or any(ord(char) < 32 for char in model):
            raise ValueError("AI reservations need a valid model identifier.")
        if not 1 <= len(purpose) <= 64 or any(ord(char) < 32 for char in purpose):
            raise ValueError("AI reservations need a valid purpose.")
        # A no-op update is the portable lock primitive used elsewhere in the app. It
        # makes a policy edit and this admission decision share one serialised boundary.
        await self._session.execute(
            update(AiUsagePolicyRow)
            .where(AiUsagePolicyRow.id == policy_id)
            .values(updated_at=AiUsagePolicyRow.updated_at)
        )
        policy = await self.get_policy(policy_id)
        if policy is None:
            raise NotFound()
        if not policy.enabled:
            raise AiAllowanceExceeded(policy)
        start, end = period_bounds(now, policy.period)
        insert = (
            pg_insert if self._session.get_bind().dialect.name == "postgresql" else sqlite_insert
        )
        await self._session.execute(
            insert(AiUsageCounterRow)
            .values(
                policy_id=policy.id,
                period_start=start,
                period_end=end,
                used_requests=0,
                reserved_requests=0,
                used_tokens=0,
                reserved_tokens=0,
            )
            .on_conflict_do_nothing(index_elements=["policy_id", "period_start"])
        )
        constraints = [
            AiUsageCounterRow.policy_id == policy.id,
            AiUsageCounterRow.period_start == start,
        ]
        if policy.request_limit is not None:
            constraints.append(
                AiUsageCounterRow.used_requests + AiUsageCounterRow.reserved_requests + 1
                <= policy.request_limit
            )
        if policy.token_limit is not None:
            constraints.append(
                AiUsageCounterRow.used_tokens + AiUsageCounterRow.reserved_tokens + requested_tokens
                <= policy.token_limit
            )
        result = await self._session.execute(
            update(AiUsageCounterRow)
            .where(*constraints)
            .values(
                reserved_requests=AiUsageCounterRow.reserved_requests + 1,
                reserved_tokens=AiUsageCounterRow.reserved_tokens + requested_tokens,
            )
        )
        if _rowcount(result) != 1:
            raise AiAllowanceExceeded(policy)
        reservation = AiUsageReservationRow(
            id=uuid4(),
            policy_id=policy.id,
            user_id=user_id,
            profile_id=profile_id,
            model=model,
            purpose=purpose,
            period_start=start,
            period_end=end,
            reserved_tokens=requested_tokens,
            status=AiReservationStatus.RESERVED.value,
            created_at=now,
        )
        self._session.add(reservation)
        await self._session.flush()
        return _reservation(reservation)

    async def settle(
        self,
        reservation_id: UUID,
        *,
        ok: bool,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        error: str | None,
        now: datetime,
    ) -> AiUsageReservation:
        """Move a reservation into used counters exactly once, safely on retries."""
        prompt, completion = token_count(prompt_tokens), token_count(completion_tokens)
        row = await self._session.get(AiUsageReservationRow, reservation_id, populate_existing=True)
        if row is None:
            raise NotFound()
        if row.status == AiReservationStatus.SETTLED.value:
            return _reservation(row)
        actual = (
            prompt + completion
            if prompt is not None and completion is not None
            else row.reserved_tokens
        )
        result = await self._session.execute(
            update(AiUsageReservationRow)
            .where(
                AiUsageReservationRow.id == reservation_id,
                AiUsageReservationRow.status == AiReservationStatus.RESERVED.value,
            )
            .values(
                status=AiReservationStatus.SETTLED.value,
                settled_at=now,
                prompt_tokens=prompt,
                completion_tokens=completion,
                actual_tokens=actual,
                ok=ok,
                error=error[:120] if error else None,
            )
        )
        if _rowcount(result) != 1:
            current = await self._session.get(AiUsageReservationRow, reservation_id)
            if current is None:
                raise NotFound()
            return _reservation(current)
        counter = await self._session.get(
            AiUsageCounterRow, (row.policy_id, row.period_start), populate_existing=True
        )
        if (
            counter is None
            or counter.reserved_requests < 1
            or counter.reserved_tokens < row.reserved_tokens
        ):
            raise ValueError("AI usage counter is inconsistent with its reservation.")
        counter.reserved_requests -= 1
        counter.reserved_tokens -= row.reserved_tokens
        counter.used_requests += 1
        counter.used_tokens += actual
        await self._session.flush()
        row = await self._session.get(AiUsageReservationRow, reservation_id, populate_existing=True)
        assert row is not None  # noqa: S101 - row was atomically updated above
        return _reservation(row)

    async def summary(
        self, user_id: UUID, *, now: datetime, team_id: UUID | None = None
    ) -> list[AiUsageSummary]:
        policies = await self.effective_policies(user_id, team_id=team_id)
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
                )
            )
        return result

    async def list_reservations(self, limit: int = 100) -> list[AiUsageReservation]:
        rows = await self._session.scalars(
            select(AiUsageReservationRow)
            .order_by(AiUsageReservationRow.created_at.desc())
            .limit(limit)
        )
        return [_reservation(row) for row in rows]
