"""Preview-bound scoped removal, permanent identities and preservation decisions."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from ase.adapters.persistence.models import AuditLogRow, ReportRow, ReportVersionRow, UserRow
from ase.adapters.persistence.private_review_models import PrivateDataReviewRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.domain.errors import Conflict, Forbidden, NotFound
from ase.domain.private_removal import RemovalRequest, RemovalScope, ReviewDecision, ReviewPurpose
from private_removal_helpers import apply, authorise, preview, report
from report_job_helpers import job


async def test_report_removal_is_preview_bound_and_leaves_other_reports(container, user, admin):
    await authorise(container, admin, user)
    target, version = await report(container, user)
    other, _ = await report(container, admin)
    request = RemovalRequest(user.id, RemovalScope.REPORT, target.id)
    plan = await preview(container, admin, request)
    assert not plan.blockers
    assert plan.counts["reports"] == plan.counts["report_versions"] == 1
    assert target.title not in str(plan)
    with pytest.raises(Conflict, match="preview changed"):
        await apply(container, admin, request, "0" * 64)
    counts = await apply(container, admin, request, plan.fingerprint)
    assert counts == plan.counts
    async with container.session_factory() as session:
        assert await session.get(ReportRow, target.id) is None
        assert await session.get(ReportVersionRow, version.id) is None
        assert await session.get(ReportRow, other.id) is not None
        audit = await session.scalar(
            select(AuditLogRow).where(AuditLogRow.action == "private_data_removed")
        )
        assert audit.details["fingerprint"] == plan.fingerprint


async def test_preview_rechecks_contents_not_just_counts(container, user, admin):
    await authorise(container, admin, user)
    target, _ = await report(container, user)
    request = RemovalRequest(user.id, RemovalScope.REPORT, target.id)
    plan = await preview(container, admin, request)
    async with container.session_factory() as session:
        await session.execute(
            update(ReportRow).where(ReportRow.id == target.id).values(title="Changed")
        )
        await session.commit()
    with pytest.raises(Conflict, match="preview changed"):
        await apply(container, admin, request, plan.fingerprint)


async def test_account_becomes_permanent_minimal_identity(container, user, admin):
    await authorise(container, admin, user, inactive=True)
    target, _ = await report(container, user)
    request = RemovalRequest(user.id, RemovalScope.ACCOUNT)
    plan = await preview(container, admin, request)
    assert not plan.blockers
    await apply(container, admin, request, plan.fingerprint)
    async with container.session_factory() as session:
        row = await session.get(UserRow, user.id)
        assert row.email != user.email and row.display_name == "Removed account"
        assert not row.is_active and row.password_hash is None
        assert row.security_version == user.security_version + 1
        assert (await session.get(PrivateDataReviewRow, user.id)).erased_at == container.clock.now()
        assert await session.get(ReportRow, target.id) is None
    assert "account_already_removed" in (await preview(container, admin, request)).blockers


@pytest.mark.parametrize(
    "decision,blocker",
    [
        (ReviewDecision.HOLD, "preservation_hold"),
        (ReviewDecision.RETAIN, "removal_not_authorised_by_review"),
    ],
)
async def test_hold_never_expires_into_permission(container, user, admin, clock, decision, blocker):
    await authorise(container, admin, user, inactive=True, decision=decision)
    clock.advance(timedelta(days=100))
    request = RemovalRequest(user.id, RemovalScope.ACCOUNT)
    plan = await preview(container, admin, request)
    assert blocker in plan.blockers
    with pytest.raises(Conflict, match="blocked"):
        await apply(container, admin, request, plan.fingerprint)


async def test_review_is_compare_and_set_and_account_must_be_inactive(
    container, user, admin, clock
):
    request = RemovalRequest(user.id, RemovalScope.ACCOUNT)
    assert "necessity_review_required" in (await preview(container, admin, request)).blockers
    await authorise(container, admin, user)
    assert "deactivate_account_first" in (await preview(container, admin, request)).blockers
    with pytest.raises(Conflict, match="review changed"):
        await authorise(container, admin, user)
    clock.advance(timedelta(days=90))
    assert "necessity_review_due" in (await preview(container, admin, request)).blockers
    async with container.session_factory() as session:
        review = await container.private_removal(session).review(
            admin, user.id, ReviewDecision.HOLD, ReviewPurpose.QUARTERLY, 1
        )
        assert review.revision == 2


async def test_non_admin_and_wrong_owner_cannot_remove(container, user, admin):
    target, _ = await report(container, admin)
    with pytest.raises(Forbidden):
        await preview(container, user, RemovalRequest(user.id, RemovalScope.ACCOUNT))
    with pytest.raises(NotFound):
        await preview(container, admin, RemovalRequest(user.id, RemovalScope.REPORT, target.id))
    with pytest.raises(NotFound):
        await preview(container, admin, RemovalRequest(uuid4(), RemovalScope.ACCOUNT))


@pytest.mark.parametrize("status", ["queued", "paused", "failed", "completed"])
async def test_job_scope_blocks_active_and_deletes_only_inactive_checkpoint(
    container, user, admin, status
):
    await authorise(container, admin, user)
    target, version = await report(container, user)
    checkpoint = job(owner_id=user.id, status=status, report_id=target.id, version_id=version.id)
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(checkpoint)
        await session.commit()
    request = RemovalRequest(user.id, RemovalScope.JOB, checkpoint.id)
    plan = await preview(container, admin, request)
    if status == "queued":
        assert "active_uncertain_or_unverifiable_job" in plan.blockers
        return
    assert not plan.blockers
    await apply(container, admin, request, plan.fingerprint)
    async with container.session_factory() as session:
        assert await SqlReportJobRepository(session).get(checkpoint.id) is None
        assert await session.get(ReportRow, target.id) is not None
