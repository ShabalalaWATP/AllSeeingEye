"""Unknown reservations return their held tokens after a fixed, documented bound."""

from __future__ import annotations

from datetime import timedelta

import pytest

from ai_usage_helpers import accounting, add_policy, policy, reservations, summaries
from ase.adapters.persistence.ai_usage_unknown import RESOLVED_UNKNOWN_ERROR
from ase.application.ai_usage_gateway import AllowanceLlmGateway
from ase.application.ports.llm import LlmGatewayTimeout
from ase.domain.ai_usage import (
    UNKNOWN_RESOLUTION_AGE,
    AiAllowanceExceeded,
    AiAttribution,
    AiReservationStatus,
)
from report_job_budget_helpers import REQUEST


class TimingOut:
    async def complete(self, *_args):
        raise LlmGatewayTimeout("slow")


async def timed_out_call(container, user) -> None:
    wrapped = AllowanceLlmGateway(
        TimingOut(),
        accounting(container),
        attribution=AiAttribution.actor(user.id),
        profile_id=None,
    )
    with pytest.raises(LlmGatewayTimeout):
        await wrapped.complete("https://model.example", "secret", "luna", REQUEST)


async def test_unknown_reservation_is_held_until_the_bound(container, user, clock):
    await add_policy(container, policy(limit=5, tokens=100_000))
    await timed_out_call(container, user)
    clock.advance(UNKNOWN_RESOLUTION_AGE - timedelta(minutes=1))
    outcome = await accounting(container).reconcile()
    assert outcome.resolved == 0
    [row] = await reservations(container)
    assert row.status is AiReservationStatus.UNKNOWN
    [summary] = await summaries(container, user.id)
    assert (summary.reserved_requests, summary.used_requests) == (1, 0)


async def test_old_unknown_reservation_counts_the_request_and_frees_its_tokens(
    container, user, clock
):
    await add_policy(container, policy(limit=5, tokens=100_000))
    await timed_out_call(container, user)
    clock.advance(UNKNOWN_RESOLUTION_AGE + timedelta(minutes=1))
    ledger = accounting(container)
    assert (await ledger.reconcile()).resolved == 1
    [row] = await reservations(container)
    assert (row.status, row.actual_tokens, row.ok, row.error) == (
        AiReservationStatus.SETTLED,
        0,
        False,
        RESOLVED_UNKNOWN_ERROR,
    )
    [summary] = await summaries(container, user.id)
    assert (summary.reserved_requests, summary.reserved_tokens) == (0, 0)
    assert (summary.used_requests, summary.used_tokens) == (1, 0)
    async with container.session_factory() as session:
        totals = await container.repositories(session).ai_usage.account_totals(user.id, clock.now())
    # The observed history still records an unknown request, never an invented charge.
    assert (totals.unknown_requests, totals.used_requests) == (1, 0)
    assert (await ledger.reconcile()).resolved == 0


async def test_resolution_lets_a_token_bound_allowance_admit_again(container, user, clock):
    allowance = 1_000_000
    await add_policy(container, policy(limit=None, tokens=allowance))
    await timed_out_call(container, user)
    [held] = await reservations(container)
    remainder = allowance - held.reserved_tokens + 1
    ledger = accounting(container)
    attribution = AiAttribution.actor(user.id)
    with pytest.raises(AiAllowanceExceeded):
        await ledger.reserve(
            attribution, profile_id=None, model="m", purpose="t", requested_tokens=remainder
        )
    clock.advance(UNKNOWN_RESOLUTION_AGE + timedelta(minutes=1))
    await ledger.reconcile()
    batch = await ledger.reserve(
        attribution, profile_id=None, model="m", purpose="t", requested_tokens=remainder
    )
    assert len(batch.reservations) == 1
