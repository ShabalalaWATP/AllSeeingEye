"""Immutable references, other people's records and linked subscription ownership."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from ase.adapters.persistence.library_models import ResearchLibraryRow
from ase.adapters.persistence.models import ReportRow, ReportVersionRow, ScheduleRow
from ase.adapters.persistence.original_passage_models import OriginalPassageRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.research_brief_models import ResearchBriefRevisionRow
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionDeliveryRow,
    SubscriptionEditionRow,
)
from ase.adapters.persistence.teams import TeamMembershipRow
from ase.domain.private_removal import RemovalRequest, RemovalScope
from ase.domain.research_brief_scope import BriefScope
from private_removal_helpers import apply, authorise, brief, preview, report, subscription
from report_job_helpers import job
from team_helpers import CONTEXT, team_service


@pytest.mark.parametrize("path", ["parent_report_id", "research_reuse", "map_origin", "free_text"])
async def test_exact_saved_references_block_but_free_text_does_not(container, user, admin, path):
    await authorise(container, admin, user)
    target, version = await report(container, user)
    scope = {path: str(target.id)}
    if path in {"research_reuse", "map_origin"}:
        scope[path] = {"report_id": str(target.id), "report_version_id": str(version.id)}
    await report(container, admin, scope=scope)
    plan = await preview(container, admin, RemovalRequest(user.id, RemovalScope.REPORT, target.id))
    assert ("retained_structured_reference" in plan.blockers) == (path != "free_text")


async def test_other_persons_library_notes_block_report_deletion(container, user, admin):
    await authorise(container, admin, user)
    target, _ = await report(container, user)
    async with container.session_factory() as session:
        session.add(
            ResearchLibraryRow(
                user_id=admin.id,
                report_id=target.id,
                favourite=True,
                note="Keep my review",
                updated_at=container.clock.now(),
            )
        )
        await session.commit()
    plan = await preview(container, admin, RemovalRequest(user.id, RemovalScope.REPORT, target.id))
    assert "other_person_record" in plan.blockers


async def test_account_retains_shared_report_and_checks_last_manager(container, user, admin):
    async with team_service(container) as service:
        team = await service.create(user, "Shared desk", CONTEXT)
    shared, _ = await report(container, user, team_id=team.id)
    await authorise(container, admin, user, inactive=True)
    request = RemovalRequest(user.id, RemovalScope.ACCOUNT)
    assert "last_active_team_manager" in (await preview(container, admin, request)).blockers
    async with container.session_factory() as session:
        session.add(
            TeamMembershipRow(
                team_id=team.id, user_id=admin.id, role="manager", joined_at=container.clock.now()
            )
        )
        await session.commit()
    plan = await preview(container, admin, request)
    assert not plan.blockers
    await apply(container, admin, request, plan.fingerprint)
    async with container.session_factory() as session:
        assert await session.get(ReportRow, shared.id) is not None
        assert await session.get(TeamMembershipRow, (team.id, user.id)) is None
        assert await session.get(TeamMembershipRow, (team.id, admin.id)) is not None


async def test_job_only_removal_preserves_linked_excerpts(container, user, admin):
    await authorise(container, admin, user)
    target, version = await report(container, user)
    checkpoint = job(
        owner_id=user.id, status="completed", report_id=target.id, version_id=version.id
    )
    now = container.clock.now()
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(checkpoint)
        session.add(
            OriginalPassageRow(
                id=uuid4(),
                job_id=checkpoint.id,
                report_version_id=version.id,
                owner_id=user.id,
                team_id=None,
                source_id="example",
                event_id="event",
                evidence_label="E1",
                candidate_id="candidate",
                document_version_id="a" * 64,
                passage_id="b" * 64,
                snapshot={"text": "Keep this excerpt"},
                snapshot_sha256="c" * 64,
                created_at=now,
                expires_at=now + timedelta(days=7),
            )
        )
        await session.commit()
    request = RemovalRequest(user.id, RemovalScope.JOB, checkpoint.id)
    assert (
        "job_excerpts_used_by_retained_report"
        in (await preview(container, admin, request)).blockers
    )
    request = RemovalRequest(user.id, RemovalScope.REPORT, target.id)
    plan = await preview(container, admin, request)
    assert not plan.blockers
    await apply(container, admin, request, plan.fingerprint)
    async with container.session_factory() as session:
        assert await session.scalar(select(OriginalPassageRow.id)) is None


@pytest.mark.parametrize("state", ["pending", "sending", "uncertain"])
async def test_archived_subscription_includes_output_and_fences_delivery(
    container, user, admin, state
):
    await authorise(container, admin, user)
    target, version = await report(container, user)
    checkpoint = job(
        owner_id=user.id, status="completed", report_id=target.id, version_id=version.id
    )
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(checkpoint)
        await session.commit()
    schedule, edition = await subscription(
        container, user, report_id=target.id, job_id=checkpoint.id
    )
    now = container.clock.now()
    async with container.session_factory() as session:
        session.add(
            SubscriptionDeliveryRow(
                id=uuid4(),
                edition_id=edition.id,
                channel="email",
                destination_ref=user.id,
                event_kind="edition_ready",
                idempotency_key=uuid4(),
                state=state,
                attempts=1,
                created_at=now,
                updated_at=now,
                lease_token=uuid4(),
                next_attempt_at=None,
                safe_reason=None,
            )
        )
        await session.commit()
    request = RemovalRequest(user.id, RemovalScope.SUBSCRIPTION, schedule.id)
    plan = await preview(container, admin, request)
    if state != "pending":
        assert "active_or_uncertain_delivery" in plan.blockers
        return
    assert not plan.blockers
    assert plan.counts["reports"] == plan.counts["report_jobs"] == 1
    await apply(container, admin, request, plan.fingerprint)
    async with container.session_factory() as session:
        for model in (
            SubscriptionDeliveryRow,
            SubscriptionEditionRow,
            ScheduleRow,
            ReportRow,
            ReportVersionRow,
        ):
            assert await session.scalar(select(model)) is None


async def test_unarchived_subscription_and_external_baseline_are_blocked(container, user, admin):
    await authorise(container, admin, user)
    target, version = await report(container, user)
    schedule, edition = await subscription(container, user, archived=False)
    request = RemovalRequest(user.id, RemovalScope.SUBSCRIPTION, schedule.id)
    assert "archive_subscriptions_first" in (await preview(container, admin, request)).blockers
    async with container.session_factory() as session:
        await session.execute(
            update(SubscriptionEditionRow)
            .where(SubscriptionEditionRow.id == edition.id)
            .values(baseline_version_id=version.id)
        )
        await session.commit()
    request = RemovalRequest(user.id, RemovalScope.REPORT, target.id)
    assert "retained_foreign_key_dependency" in (await preview(container, admin, request)).blockers


async def test_brief_removal_respects_surviving_report_reference(container, user, admin):
    await authorise(container, admin, user)
    value = await brief(container, user)
    target, version = await report(container, user)
    async with container.session_factory() as session:
        await session.execute(
            update(ReportVersionRow)
            .where(ReportVersionRow.id == version.id)
            .values(analysis={"brief_reference": {"id": str(value.identity.id), "revision": 1}})
        )
        await session.commit()
    request = RemovalRequest(user.id, RemovalScope.BRIEF, value.identity.id)
    assert "retained_structured_reference" in (await preview(container, admin, request)).blockers
    report_request = RemovalRequest(user.id, RemovalScope.REPORT, target.id)
    plan = await preview(container, admin, report_request)
    assert not plan.blockers
    await apply(container, admin, report_request, plan.fingerprint)
    plan = await preview(container, admin, request)
    assert not plan.blockers
    await apply(container, admin, request, plan.fingerprint)
    async with container.session_factory() as session:
        assert await session.scalar(select(ResearchBriefRevisionRow)) is None


async def test_brief_handoff_numeric_versions_are_valid_references(container, user, admin):
    await authorise(container, admin, user)
    target, _ = await report(container, user)
    await brief(container, user, scope=BriefScope(origin_report_id=target.id, origin_version=1))
    plan = await preview(container, admin, RemovalRequest(user.id, RemovalScope.REPORT, target.id))
    assert "retained_structured_reference" in plan.blockers
    assert "unverifiable_structured_reference" not in plan.blockers


@pytest.mark.parametrize("linked_owner", ["foreign_job", "foreign_report", "retained_schedule"])
async def test_malformed_cross_owner_links_never_expand_private_removal(
    container, user, admin, linked_owner
):
    await authorise(container, admin, user)
    target, version = await report(container, admin if linked_owner == "foreign_report" else user)
    checkpoint = job(
        owner_id=admin.id if linked_owner == "foreign_job" else user.id,
        status="completed",
        report_id=target.id,
        version_id=version.id,
    )
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(checkpoint)
        await session.commit()
    schedule, _ = await subscription(
        container,
        user,
        report_id=target.id if linked_owner == "foreign_report" else None,
        job_id=checkpoint.id if linked_owner != "retained_schedule" else None,
    )
    request = RemovalRequest(user.id, RemovalScope.SUBSCRIPTION, schedule.id)
    expected = (
        "shared_or_foreign_job_dependency"
        if linked_owner == "foreign_job"
        else "shared_or_foreign_report_dependency"
    )
    if linked_owner == "retained_schedule":
        async with container.session_factory() as session:
            await session.execute(
                update(ScheduleRow)
                .where(ScheduleRow.id == schedule.id)
                .values(last_report_id=target.id)
            )
            await session.commit()
        request = RemovalRequest(user.id, RemovalScope.REPORT, target.id)
        expected = "retained_saved_work_dependency"
    plan = await preview(container, admin, request)
    assert expected in plan.blockers
    async with container.session_factory() as session:
        assert await session.get(ReportRow, target.id) is not None
