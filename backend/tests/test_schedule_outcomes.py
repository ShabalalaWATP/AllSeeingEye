"""Scheduled editions preserve their actual saved outcome and successful baseline."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from ase.adapters.persistence.schedules import SqlScheduleStore
from ase.api.schemas_schedules import ScheduleOut
from ase.application.schedules.manage import ScheduleInput, build_schedule
from ase.application.schedules.report_request import scheduled_report_request
from ase.container import Container
from ase.container.subscription_enqueue import SubscriptionAdmission
from ase.domain.reports import ReportStatus
from ase.domain.research import CollectionAttempt, CollectionStatus
from ase.domain.research_records import ResearchReceipt
from ase.domain.schedules import CoverageState, ScheduleRunResult, next_run_after
from ase.domain.users import User
from report_documents_helpers import document_records
from team_helpers import CONTEXT


async def _schedule(container: Container, owner: User):
    async with container.session_factory() as session:
        return await container.create_schedule(session).execute(
            owner,
            ScheduleInput(
                name="Daily research",
                template_id="intsum",
                country_iso="UA",
                question="What changed?",
                notify_on_change=True,
            ),
            CONTEXT,
        )


async def _saved_version(
    container: Container, owner: User, status: ReportStatus, *, partial: bool = False
):
    record, version = document_records(owner.id)
    record.status = status
    version.status = status
    if partial:
        version.research = ResearchReceipt(
            "What changed?",
            "quick",
            "general",
            ("en",),
            (),
            container.clock.now() - timedelta(days=1),
            container.clock.now(),
            (CollectionAttempt("source", "Source", CollectionStatus.UNAVAILABLE),),
            0,
        )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record, version


async def _run_saved(container: Container, schedule, record, version):
    container.clock.advance(timedelta(days=1))
    now = container.clock.now()
    await SqlScheduleStore(container.session_factory, container.access_policy).mark_run(
        schedule.id,
        ran_at=now,
        next_run_at=next_run_after(
            now,
            schedule.hour_utc,
            schedule.cadence,
            schedule.weekday,
            schedule.monthday,
            schedule.anchor_month,
        ),
        result=ScheduleRunResult.from_version(
            version, research_required=schedule.research_mode is not None
        ),
        error_code=None,
        expected=schedule,
    )
    async with container.session_factory() as session:
        return await container.repositories(session).schedules.get(schedule.id)


@pytest.mark.parametrize(
    ("status", "partial", "error_code", "coverage"),
    [
        (ReportStatus.FAILED, False, "report_failed", "not_applicable"),
        (ReportStatus.NEEDS_REVIEW, False, "review_required", "not_applicable"),
        (ReportStatus.READY, True, "partial_coverage", "partial"),
        (ReportStatus.READY, False, None, "not_applicable"),
    ],
)
async def test_saved_version_outcome_is_visible_and_only_complete_ready_advances_baseline(
    container: Container,
    user: User,
    status: ReportStatus,
    partial: bool,
    error_code: str | None,
    coverage: str,
) -> None:
    schedule = await _schedule(container, user)
    record, version = await _saved_version(container, user, status, partial=partial)
    current = await _run_saved(container, schedule, record, version)
    assert current is not None
    assert current.last_report_id == record.id
    assert current.last_version_id == version.id
    assert current.last_outcome == status
    assert current.last_coverage == coverage
    assert current.last_error == error_code
    projected = ScheduleOut.from_schedule(current)
    assert projected.last_version_id == version.id
    assert projected.last_outcome == status
    assert projected.last_coverage == coverage
    assert (current.baseline_report_id == record.id) is (error_code is None)
    assert (current.last_change is not None) is (error_code is None)
    assert bool(current.seen_content_signatures) is (error_code is None)


async def test_failed_version_keeps_prior_successful_baseline(
    container: Container, user: User
) -> None:
    schedule = await _schedule(container, user)
    ready_record, ready_version = await _saved_version(container, user, ReportStatus.READY)
    current = await _run_saved(container, schedule, ready_record, ready_version)
    assert current is not None
    baseline = current.baseline_report_id
    fingerprints = current.seen_content_signatures
    change = current.last_change
    failed_record, failed_version = await _saved_version(container, user, ReportStatus.FAILED)
    current = await _run_saved(container, current, failed_record, failed_version)
    assert current is not None
    assert current.last_report_id == failed_record.id
    assert current.baseline_report_id == baseline
    assert current.seen_content_signatures == fingerprints
    assert current.last_change == change
    assert scheduled_report_request(current).subscription_previous_report_id == baseline


async def test_enqueue_exception_keeps_due_slot_without_logging_private_error(
    container: Container, user: User, caplog
) -> None:
    schedule = await _schedule(container, user)
    container.clock.advance(timedelta(days=1))

    with patch.object(
        SubscriptionAdmission, "enqueue", side_effect=RuntimeError("token=secret-value")
    ):
        assert await container.schedule_runner.run_once() == 0
    async with container.session_factory() as session:
        current = await container.repositories(session).schedules.get(schedule.id)
    assert current is not None
    assert current.last_error is None
    assert current.last_report_id is None
    assert current.baseline_report_id is None
    assert current.next_run_at == schedule.next_run_at
    assert "secret-value" not in caplog.text


async def test_unsaved_or_mismatched_result_cannot_be_recorded(
    container: Container, user: User
) -> None:
    schedule = await _schedule(container, user)
    record, version = await _saved_version(container, user, ReportStatus.FAILED)
    forged = ScheduleRunResult(
        record.id, version.id, ReportStatus.READY, CoverageState.NOT_APPLICABLE, None
    )
    await SqlScheduleStore(container.session_factory, container.access_policy).mark_run(
        schedule.id,
        ran_at=container.clock.now(),
        next_run_at=container.clock.now() + timedelta(days=1),
        result=forged,
        error_code=None,
        expected=schedule,
    )
    async with container.session_factory() as session:
        current = await container.repositories(session).schedules.get(schedule.id)
    assert current == schedule


@pytest.mark.parametrize("overdue", [False, True])
def test_rename_preserves_pending_slot_and_run_state(overdue: bool) -> None:
    now = datetime(2026, 9, 14, 12, tzinfo=UTC)
    data = ScheduleInput(name="Original", template_id="intsum", country_iso="UA")
    original = build_schedule(
        data,
        schedule_id=uuid4(),
        owner=uuid4(),
        created=now,
        now=now,
    )
    due = now - timedelta(days=5) if overdue else original.next_run_at
    report_id, version_id = uuid4(), uuid4()
    original = replace(
        original,
        next_run_at=due,
        last_report_id=report_id,
        last_version_id=version_id,
        last_outcome=ReportStatus.NEEDS_REVIEW,
        last_coverage="partial",
        last_error="review_required",
        baseline_report_id=uuid4(),
        seen_content_signatures=("fingerprint",),
    )
    updated = build_schedule(
        replace(data, name="Renamed"),
        schedule_id=original.id,
        owner=original.created_by,
        created=original.created_at,
        now=now,
        previous=original,
    )
    assert updated.name == "Renamed"
    assert updated.next_run_at == due
    assert updated.last_report_id == report_id
    assert updated.last_version_id == version_id
    assert updated.last_outcome == ReportStatus.NEEDS_REVIEW
    assert updated.last_coverage == "partial"
    assert updated.last_error == "review_required"
    assert updated.baseline_report_id == original.baseline_report_id
    assert updated.seen_content_signatures == ("fingerprint",)


def test_cadence_edit_reschedules_explicitly() -> None:
    now = datetime(2026, 9, 14, 12, tzinfo=UTC)
    data = ScheduleInput(name="Original", template_id="intsum", country_iso="UA")
    original = build_schedule(
        data,
        schedule_id=uuid4(),
        owner=uuid4(),
        created=now,
        now=now,
    )
    original = replace(original, next_run_at=now - timedelta(days=5))
    updated = build_schedule(
        replace(data, cadence="weekly", weekday=2),
        schedule_id=original.id,
        owner=original.created_by,
        created=original.created_at,
        now=now,
        previous=original,
    )
    assert updated.next_run_at == datetime(2026, 9, 16, 6, tzinfo=UTC)


def test_research_receipt_is_required_for_complete_coverage() -> None:
    _, version = document_records()
    version.status = ReportStatus.READY
    missing = ScheduleRunResult.from_version(version, research_required=True)
    assert missing.coverage is CoverageState.PARTIAL
    assert missing.error_code == "partial_coverage"
    version.research = ResearchReceipt(
        "What changed?",
        "quick",
        "general",
        ("en",),
        (),
        datetime(2026, 9, 13, tzinfo=UTC),
        datetime(2026, 9, 14, tzinfo=UTC),
        (CollectionAttempt("source", "Source", CollectionStatus.COMPLETED),),
        1,
    )
    complete = ScheduleRunResult.from_version(version, research_required=True)
    assert complete.coverage is CoverageState.COMPLETE
    assert complete.error_code is None
