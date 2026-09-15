"""Automation rechecks origin authority before alerts, notifications and report links."""

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from ase.adapters.persistence.schedules import SqlScheduleStore
from ase.adapters.persistence.warning import SqlWarningStore
from ase.application.warning.evaluator import IndicatorEvaluator
from ase.container import Container
from ase.domain.reports import ReportStatus
from ase.domain.schedules import CoverageState, ScheduleRunResult
from ase.domain.users import User
from ase.domain.warning import Alert, Indicator, alert_from, evaluate
from report_documents_helpers import document_records
from team_helpers import CONTEXT, team_service
from tracker_helpers import conflict_events
from warning_scope_helpers import WarningActors, create_indicator, create_schedule
from warning_scope_helpers import warning_actors as warning_actors  # noqa: PLC0414


def firing_alert(container: Container, rule: Indicator) -> Alert:
    firing = evaluate(rule, conflict_events(container.clock.now()), container.clock.now(), None)
    assert firing
    return alert_from(rule, firing, uuid4(), container.clock.now())


async def saved_report(container: Container, owner: User, team_id: UUID | None) -> UUID:
    record, version = document_records(owner.id)
    record.team_id = team_id
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record.id


async def run_result(container: Container, report_id: UUID) -> ScheduleRunResult:
    async with container.session_factory() as session:
        version = await container.repositories(session).reports.get_version(report_id, 1)
    return (
        ScheduleRunResult.from_version(version)
        if version is not None
        else ScheduleRunResult(
            report_id, uuid4(), ReportStatus.READY, CoverageState.NOT_APPLICABLE, None
        )
    )


@pytest.mark.parametrize("revocation", ["membership", "archive", "deactivation"])
async def test_background_stops_after_origin_authority_is_revoked(
    container: Container,
    admin: User,
    warning_actors: WarningActors,
    revocation: str,
) -> None:
    actors = warning_actors
    rule = await create_indicator(container, actors.owner, actors.team.id)
    schedule = await create_schedule(container, actors.owner, actors.team.id)
    warning = SqlWarningStore(container.session_factory, container.access_policy)
    schedules = SqlScheduleStore(container.session_factory, container.access_policy)
    assert await warning.can_run(rule) and await schedules.can_run(schedule)
    alert = firing_alert(container, rule)
    assert await warning.add_alert(alert, rule)
    report_id = await saved_report(container, actors.owner, actors.team.id)
    if revocation == "deactivation":
        async with container.session_factory() as session:
            await container.update_user(session).execute(
                admin, actors.owner.id, None, False, CONTEXT
            )
    else:
        async with team_service(container) as service:
            if revocation == "membership":
                await service.remove_member(admin, actors.team.id, actors.owner.id, CONTEXT)
            else:
                await service.update(
                    admin, actors.team.id, name=None, is_active=False, context=CONTEXT
                )
    assert not await warning.can_run(rule) and not await schedules.can_run(schedule)
    assert not await warning.add_alert(replace(alert, id=uuid4()), rule)
    assert not await warning.attach_report(alert.id, report_id)
    await schedules.mark_run(
        schedule.id,
        ran_at=container.clock.now(),
        next_run_at=container.clock.now() + timedelta(days=2),
        result=await run_result(container, report_id),
        error_code=None,
        expected=schedule,
    )
    async with container.session_factory() as session:
        repos = container.repositories(session)
        current = await repos.schedules.get(schedule.id)
        stored = await repos.alerts.get(alert.id)
        assert current and current.last_run_at is None and current.last_report_id is None
        assert stored and stored.report_id is None


async def test_report_links_cannot_cross_personal_or_team_scope(
    container: Container,
    warning_actors: WarningActors,
) -> None:
    actors = warning_actors
    rule = await create_indicator(container, actors.owner, actors.team.id)
    schedule = await create_schedule(container, actors.owner, actors.team.id)
    warning = SqlWarningStore(container.session_factory, container.access_policy)
    schedules = SqlScheduleStore(container.session_factory, container.access_policy)
    alert = firing_alert(container, rule)
    assert await warning.add_alert(alert, rule)
    other = await saved_report(container, actors.outsider, actors.other.id)
    personal = await saved_report(container, actors.owner, None)
    valid = await saved_report(container, actors.peer, actors.team.id)
    for report_id in (other, personal, uuid4()):
        assert not await warning.attach_report(alert.id, report_id)
        await schedules.mark_run(
            schedule.id,
            ran_at=container.clock.now(),
            next_run_at=container.clock.now() + timedelta(days=2),
            result=await run_result(container, report_id),
            error_code=None,
            expected=schedule,
        )
    async with container.session_factory() as session:
        current = await container.repositories(session).schedules.get(schedule.id)
        assert current and current.last_run_at is None
    assert await warning.attach_report(alert.id, valid)
    await schedules.mark_run(
        schedule.id,
        ran_at=container.clock.now(),
        next_run_at=container.clock.now() + timedelta(days=2),
        result=await run_result(container, valid),
        error_code=None,
        expected=schedule,
    )
    async with container.session_factory() as session:
        current = await container.repositories(session).schedules.get(schedule.id)
        assert current and current.last_report_id == valid


async def test_revocation_during_notification_stops_automatic_report(
    container: Container,
    admin: User,
    warning_actors: WarningActors,
) -> None:
    actors = warning_actors
    await create_indicator(container, actors.owner, actors.team.id, report="intsum")
    container.store.upsert(conflict_events(container.clock.now()))
    reporter_calls: list[UUID] = []

    class RevokingNotifier:
        async def notify(self, alert: Alert, indicator: Indicator) -> bool:
            async with team_service(container) as service:
                await service.remove_member(admin, actors.team.id, actors.owner.id, CONTEXT)
            return True

    async def reporter(indicator: Indicator, alert: Alert) -> UUID | None:
        reporter_calls.append(indicator.id)
        return uuid4()

    evaluator = IndicatorEvaluator(
        container.store,
        SqlWarningStore(container.session_factory, container.access_policy),
        container.bus,
        RevokingNotifier(),
        container.clock,
        reporter=reporter,
    )
    fired = await evaluator.run_once()
    assert len(fired) == 1 and fired[0].created_by == actors.owner.id
    assert fired[0].team_id == actors.team.id and not reporter_calls
    assert await evaluator.run_once() == []


async def test_revocation_during_scheduled_work_prevents_report_attachment(
    container: Container,
    admin: User,
    warning_actors: WarningActors,
) -> None:
    actors = warning_actors
    schedule = await create_schedule(container, actors.owner, actors.team.id)
    report_id = await saved_report(container, actors.owner, actors.team.id)
    container.clock.advance(timedelta(days=1))
    store = SqlScheduleStore(container.session_factory, container.access_policy)
    assert await store.can_run(schedule)
    result = await run_result(container, report_id)
    async with team_service(container) as service:
        await service.remove_member(admin, actors.team.id, actors.owner.id, CONTEXT)
    assert not await store.can_run(schedule)
    await store.mark_run(
        schedule.id,
        ran_at=container.clock.now(),
        next_run_at=container.clock.now() + timedelta(days=1),
        result=result,
        error_code=None,
        expected=schedule,
    )
    async with container.session_factory() as session:
        current = await container.repositories(session).schedules.get(schedule.id)
        assert current and current.last_report_id is None and current.last_run_at is None


async def test_changed_or_deleted_origin_does_not_publish_stale_work(
    container: Container,
    warning_actors: WarningActors,
) -> None:
    actors = warning_actors
    rule = await create_indicator(container, actors.owner, actors.team.id)
    warning = SqlWarningStore(container.session_factory, container.access_policy)
    original = firing_alert(container, rule)
    async with container.session_factory() as session:
        await container.repositories(session).indicators.save(replace(rule, keywords=("new term",)))
        await session.commit()
    assert not await warning.can_run(rule)
    assert not await warning.add_alert(original, rule)
    async with container.session_factory() as session:
        await container.delete_indicator(session).execute(actors.owner, rule.id, CONTEXT)
    assert not await warning.can_run(rule)
    assert not await warning.add_alert(original, rule)
