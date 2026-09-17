"""SQL ledger for AI reservations, settlement, reconciliation and observed totals.

Every counter change is a relative, conditional ``UPDATE``.  Rows are locked in a
deterministic order: reservation rows for one call first, then policy and counter rows
sorted by policy id, then the single totals row, so concurrent workers cannot deadlock
or overwrite each other's increments.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import func, select, update

from ase.adapters.persistence.ai_usage_mapping import (
    dialect_insert,
    policy_from_row,
    reservation_from_row,
    rowcount,
)
from ase.adapters.persistence.ai_usage_models import (
    NIL_KEY,
    AiUsageCounterRow,
    AiUsagePolicyRow,
    AiUsageReservationRow,
    AiUsageTotalRow,
)
from ase.domain.ai_usage import (
    AiAllowanceExceeded,
    AiAllowancePeriod,
    AiAttribution,
    AiCallOutcome,
    AiReservationStatus,
    AiUsageReservation,
    charged_split,
    charged_tokens,
    period_bounds,
    token_count,
)
from ase.domain.errors import NotFound

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from ase.domain.ai_usage_overrides import AiPolicyOverride

_STATUS = {
    AiCallOutcome.COMPLETED: AiReservationStatus.SETTLED,
    AiCallOutcome.FAILED: AiReservationStatus.SETTLED,
    AiCallOutcome.NOT_DISPATCHED: AiReservationStatus.RELEASED,
    AiCallOutcome.UNKNOWN: AiReservationStatus.UNKNOWN,
}


def _checked_text(value: str, maximum: int, label: str) -> None:
    if not 1 <= len(value) <= maximum or any(ord(char) < 32 for char in value):
        raise ValueError(f"AI reservations need a valid {label}.")


class SqlAiLedger:
    if TYPE_CHECKING:
        _session: AsyncSession

        async def lock_policy(self, policy_id: UUID) -> bool: ...
        async def active_override(
            self, policy_id: UUID, now: datetime
        ) -> AiPolicyOverride | None: ...

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
    ) -> AiUsageReservation:
        """Atomically reserve one request and its worst-case token budget."""
        if token_count(requested_tokens) is None or requested_tokens < 1:
            raise ValueError("AI reservations need a positive bounded token amount.")
        _checked_text(model, 2048, "model identifier")
        _checked_text(purpose, 64, "purpose")
        await self.lock_policy(policy_id)
        row = await self._session.get(AiUsagePolicyRow, policy_id, populate_existing=True)
        if row is None:
            raise NotFound()
        policy = policy_from_row(row)
        if not policy.enabled:
            raise AiAllowanceExceeded(policy)
        override = await self.active_override(policy.id, now)
        request_limit, token_limit = policy.request_limit, policy.token_limit
        if override is not None:
            request_limit = override.requests.apply(request_limit)
            token_limit = override.tokens.apply(token_limit)
        start, end = period_bounds(now, policy.period)
        await self._session.execute(
            dialect_insert(self._session)(AiUsageCounterRow)
            .values(policy_id=policy.id, period_start=start, period_end=end)
            .on_conflict_do_nothing(index_elements=["policy_id", "period_start"])
        )
        counter = AiUsageCounterRow
        constraints = [counter.policy_id == policy.id, counter.period_start == start]
        if request_limit is not None:
            constraints.append(
                counter.used_requests + counter.reserved_requests + 1 <= request_limit
            )
        if token_limit is not None:
            constraints.append(
                counter.used_tokens + counter.reserved_tokens + requested_tokens <= token_limit
            )
        result = await self._session.execute(
            update(counter)
            .where(*constraints)
            .values(
                reserved_requests=counter.reserved_requests + 1,
                reserved_tokens=counter.reserved_tokens + requested_tokens,
            )
        )
        if rowcount(result) != 1:
            raise AiAllowanceExceeded(policy)
        reservation = AiUsageReservationRow(
            id=uuid4(),
            call_id=call_id,
            policy_id=policy.id,
            user_id=attribution.user_id,
            team_id=attribution.team_id,
            system=attribution.system,
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
        return reservation_from_row(reservation)

    async def mark_dispatched(self, call_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(AiUsageReservationRow)
            .where(
                AiUsageReservationRow.call_id == call_id,
                AiUsageReservationRow.status == AiReservationStatus.RESERVED.value,
                AiUsageReservationRow.dispatched_at.is_(None),
            )
            .values(dispatched_at=now)
        )

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
    ) -> None:
        """Apply a call outcome exactly once to every reservation and the observed totals."""
        rows = list(
            await self._session.scalars(
                select(AiUsageReservationRow)
                .where(AiUsageReservationRow.call_id == call_id)
                .order_by(AiUsageReservationRow.id)
                .execution_options(populate_existing=True)
            )
        )
        prompt, completion = token_count(prompt_tokens), token_count(completion_tokens)
        status = _STATUS[outcome]
        changed: list[AiUsageReservationRow] = []
        for row in rows:
            actual = charged_tokens(outcome, prompt, completion, row.reserved_tokens)
            result = await self._session.execute(
                update(AiUsageReservationRow)
                .where(
                    AiUsageReservationRow.id == row.id,
                    AiUsageReservationRow.status == AiReservationStatus.RESERVED.value,
                )
                .values(
                    status=status.value,
                    settled_at=now if status is not AiReservationStatus.UNKNOWN else None,
                    prompt_tokens=prompt,
                    completion_tokens=completion,
                    actual_tokens=actual if status is AiReservationStatus.SETTLED else None,
                    ok=outcome is AiCallOutcome.COMPLETED,
                    error=error[:120] if error else None,
                )
            )
            if rowcount(result) == 1:
                changed.append(row)
        for row in sorted(changed, key=lambda item: item.policy_id):
            await self._apply_counter(row, outcome, prompt, completion)
        if changed or not rows:
            await self._add_totals(
                attribution,
                reserved_at,
                outcome,
                charged_split(outcome, prompt, completion, requested_tokens),
            )
        await self._session.flush()

    async def _apply_counter(
        self,
        row: AiUsageReservationRow,
        outcome: AiCallOutcome,
        prompt: int | None,
        completion: int | None,
    ) -> None:
        if outcome is AiCallOutcome.UNKNOWN:
            return  # The reservation is held conservatively until reviewed.
        counter = AiUsageCounterRow
        values = {
            "reserved_requests": counter.reserved_requests - 1,
            "reserved_tokens": counter.reserved_tokens - row.reserved_tokens,
        }
        if outcome is not AiCallOutcome.NOT_DISPATCHED:
            values["used_requests"] = counter.used_requests + 1
            values["used_tokens"] = counter.used_tokens + charged_tokens(
                outcome, prompt, completion, row.reserved_tokens
            )
        result = await self._session.execute(
            update(counter)
            .where(
                counter.policy_id == row.policy_id,
                counter.period_start == row.period_start,
                counter.reserved_requests >= 1,
                counter.reserved_tokens >= row.reserved_tokens,
            )
            .values(**values)
        )
        if rowcount(result) != 1:
            raise ValueError("AI usage counter is inconsistent with its reservation.")

    async def _add_totals(
        self,
        attribution: AiAttribution,
        at: datetime,
        outcome: AiCallOutcome,
        split: tuple[int, int],
    ) -> None:
        if outcome is AiCallOutcome.NOT_DISPATCHED:
            return
        start, end = period_bounds(at, AiAllowancePeriod.MONTH)
        team_key = attribution.team_id or NIL_KEY
        user_key = attribution.user_id or NIL_KEY
        await self._session.execute(
            dialect_insert(self._session)(AiUsageTotalRow)
            .values(period_start=start, team_key=team_key, user_key=user_key, period_end=end)
            .on_conflict_do_nothing(index_elements=["period_start", "team_key", "user_key"])
        )
        total = AiUsageTotalRow
        unknown = outcome is AiCallOutcome.UNKNOWN
        input_tokens, output_tokens = (0, 0) if unknown else split
        await self._session.execute(
            update(total)
            .where(
                total.period_start == start,
                total.team_key == team_key,
                total.user_key == user_key,
            )
            .values(
                used_requests=total.used_requests + (0 if unknown else 1),
                used_tokens=total.used_tokens + input_tokens + output_tokens,
                used_input_tokens=total.used_input_tokens + input_tokens,
                used_output_tokens=total.used_output_tokens + output_tokens,
                unknown_requests=total.unknown_requests + (1 if unknown else 0),
            )
        )

    async def stale_reservations(self, before: datetime, limit: int) -> list[AiUsageReservation]:
        """One representative reservation per stale call, oldest first."""
        call_ids = list(
            await self._session.scalars(
                select(AiUsageReservationRow.call_id)
                .where(
                    AiUsageReservationRow.status == AiReservationStatus.RESERVED.value,
                    AiUsageReservationRow.created_at < before,
                )
                .group_by(AiUsageReservationRow.call_id)
                .order_by(func.min(AiUsageReservationRow.created_at))
                .limit(limit)
            )
        )
        result: list[AiUsageReservation] = []
        for call_id in call_ids:
            row = await self._session.scalar(
                select(AiUsageReservationRow)
                .where(AiUsageReservationRow.call_id == call_id)
                .order_by(AiUsageReservationRow.id)
                .limit(1)
            )
            if row is not None:
                result.append(reservation_from_row(row))
        return result

    async def count_reservations(self, status: AiReservationStatus) -> int:
        return int(
            await self._session.scalar(
                select(func.count(func.distinct(AiUsageReservationRow.call_id))).where(
                    AiUsageReservationRow.status == status.value
                )
            )
            or 0
        )

    async def list_reservations(self, limit: int = 100) -> list[AiUsageReservation]:
        rows = await self._session.scalars(
            select(AiUsageReservationRow)
            .order_by(AiUsageReservationRow.created_at.desc(), AiUsageReservationRow.id)
            .limit(limit)
        )
        return [reservation_from_row(row) for row in rows]
