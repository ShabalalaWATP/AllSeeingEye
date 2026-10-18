"""Released deliveries and open subscription attempts retain their recovery records."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_edition_models import SubscriptionAttemptRow
from ase.adapters.persistence.web_push_models import PushDeliveryRow, PushDeviceRow
from ase.domain.private_removal import RemovalRequest, RemovalScope
from private_removal_helpers import apply, authorise, preview, subscription
from report_job_helpers import job


@pytest.mark.parametrize(
    "state",
    ["pending", "sent", "refused", "expired", "cancelled", "sending", "uncertain", "unknown"],
)
async def test_push_receipts_only_remove_before_release_or_after_terminal_outcome(
    container, user, admin, state
):
    await authorise(container, admin, user, inactive=True)
    now, device_id = container.clock.now(), uuid4()
    async with container.session_factory() as session:
        session.add(
            PushDeviceRow(
                id=device_id,
                user_id=user.id,
                family_id=uuid4(),
                security_version=1,
                endpoint_hash="a" * 64,
                encrypted_subscription="synthetic",
                created_at=now,
                next_check_at=now,
            )
        )
        await session.flush()
        session.add(
            PushDeliveryRow(
                id=uuid4(),
                device_id=device_id,
                alert_id=uuid4(),
                state=state,
                lease_token=None,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()
    request = RemovalRequest(user.id, RemovalScope.ACCOUNT)
    plan = await preview(container, admin, request)
    if state in {"sending", "uncertain", "unknown"}:
        assert "active_or_uncertain_delivery" in plan.blockers
    else:
        assert not plan.blockers
        assert plan.counts["web_push_outbox"] == 1
        await apply(container, admin, request, plan.fingerprint)
        async with container.session_factory() as session:
            assert await session.scalar(select(PushDeliveryRow)) is None
            assert await session.scalar(select(PushDeviceRow)) is None


@pytest.mark.parametrize("settled", [False, True])
async def test_subscription_attempts_capture_previous_jobs_and_require_settlement(
    container, user, admin, settled
):
    await authorise(container, admin, user)
    checkpoint = job(owner_id=user.id, status="failed")
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(checkpoint)
        await session.commit()
    schedule, edition = await subscription(container, user)
    now = container.clock.now()
    async with container.session_factory() as session:
        session.add(
            SubscriptionAttemptRow(
                id=uuid4(),
                edition_id=edition.id,
                job_id=checkpoint.id,
                number=1,
                stage="complete",
                started_at=now,
                ended_at=now if settled else None,
                outcome="failed",
                reserved_requests=0,
                actual_requests=0,
                reserved_output_tokens=0,
                actual_output_tokens=0,
            )
        )
        await session.commit()
    request = RemovalRequest(user.id, RemovalScope.SUBSCRIPTION, schedule.id)
    plan = await preview(container, admin, request)
    assert plan.counts["report_jobs"] == 1
    if not settled:
        assert "unsettled_subscription_attempt" in plan.blockers
    else:
        assert not plan.blockers
        await apply(container, admin, request, plan.fingerprint)
        async with container.session_factory() as session:
            assert await SqlReportJobRepository(session).get(checkpoint.id) is None
            assert await session.scalar(select(SubscriptionAttemptRow)) is None
