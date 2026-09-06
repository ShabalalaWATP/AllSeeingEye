"""Change alerts commit once, inherit scope and stop when schedule authority is revoked."""

from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import select

from ase.adapters.persistence.models import AlertRow, ScheduleRow
from ase.adapters.persistence.schedules import SqlScheduleStore
from ase.application.schedules.manage import ScheduleInput
from ase.container import Container
from ase.domain.users import User
from helpers import USER_PASSWORD, bearer, login_token
from report_documents_helpers import document_records
from team_helpers import CONTEXT, team_service
from warning_scope_helpers import WarningActors
from warning_scope_helpers import warning_actors as warning_actors  # noqa: PLC0414


async def schedule_for(container, owner, team_id=None):
    async with container.session_factory() as session:
        return await container.create_schedule(session).execute(
            owner,
            ScheduleInput(
                name="Saved question",
                template_id="ask",
                question="What changed?",
                team_id=team_id,
                notify_on_change=True,
            ),
            CONTEXT,
        )


async def save_report(container, owner, team_id=None, *, changed=False):
    record, version = document_records(owner.id)
    record.team_id = team_id
    if changed:
        version = replace(
            version,
            evidence=(replace(version.evidence[0], content_hash="new-hash"), *version.evidence[1:]),
        )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record, version


async def mark(container, schedule, report):
    await SqlScheduleStore(container.session_factory, container.access_policy).mark_run(
        schedule.id,
        ran_at=container.clock.now(),
        next_run_at=container.clock.now() + timedelta(days=1),
        report_id=report.id,
        error=None,
        expected=schedule,
    )


async def refresh(container, owner, identity):
    async with container.session_factory() as session:
        return next(
            value
            for value in await container.list_schedules(session).execute(owner)
            if value.id == identity
        )


async def test_baseline_unchanged_and_replayed_runs_do_not_duplicate_alerts(
    container: Container, user: User
):
    schedule = await schedule_for(container, user)
    baseline, _ = await save_report(container, user)
    await mark(container, schedule, baseline)
    schedule = await refresh(container, user, schedule.id)
    assert schedule.last_change.status == "baseline"
    same, _ = await save_report(container, user)
    await mark(container, schedule, same)
    schedule = await refresh(container, user, schedule.id)
    assert schedule.last_change.status == "unchanged"
    changed, version = await save_report(container, user, changed=True)
    await mark(container, schedule, changed)
    await mark(container, schedule, changed)  # stale expected snapshot must not commit twice
    schedule = await refresh(container, user, schedule.id)
    assert schedule.last_change.status == "changed" and schedule.last_report_id == changed.id
    assert schedule.last_change.version_id == version.id
    async with container.session_factory() as session:
        alerts = list(await session.scalars(select(AlertRow)))
        assert len(alerts) == 1
        assert alerts[0].indicator_id is None and alerts[0].schedule_id == schedule.id
        assert alerts[0].created_by == user.id and alerts[0].team_id is None
        assert alerts[0].title.startswith("Evidence changed:")
    same_changed, _ = await save_report(container, user, changed=True)
    await mark(container, schedule, same_changed)
    async with container.session_factory() as session:
        assert len(list(await session.scalars(select(AlertRow)))) == 1


@pytest.mark.parametrize("revocation", ["membership", "archive", "delete", "disable", "owner"])
async def test_revoked_schedule_cannot_commit_change_alert(
    container: Container,
    admin: User,
    warning_actors: WarningActors,
    revocation: str,
):
    actors = warning_actors
    schedule = await schedule_for(container, actors.owner, actors.team.id)
    baseline, _ = await save_report(container, actors.owner, actors.team.id)
    await mark(container, schedule, baseline)
    schedule = await refresh(container, actors.owner, schedule.id)
    changed, _ = await save_report(container, actors.owner, actors.team.id, changed=True)
    if revocation in ("membership", "archive"):
        async with team_service(container) as service:
            if revocation == "membership":
                await service.remove_member(admin, actors.team.id, actors.owner.id, CONTEXT)
            else:
                await service.update(
                    admin, actors.team.id, name=None, is_active=False, context=CONTEXT
                )
    else:
        async with container.session_factory() as session:
            if revocation == "delete":
                await container.delete_schedule(session).execute(actors.owner, schedule.id, CONTEXT)
            elif revocation == "owner":
                owner = await container.repositories(session).users.get_by_id(actors.owner.id)
                owner.is_active = False
                await container.repositories(session).users.save(owner)
                await session.commit()
            else:
                row = await session.get(ScheduleRow, schedule.id)
                row.enabled = False
                await session.commit()
    await mark(container, schedule, changed)
    async with container.session_factory() as session:
        assert list(await session.scalars(select(AlertRow))) == []


async def test_team_alert_is_visible_and_acknowledgeable_only_with_current_scope(
    client,
    container: Container,
    admin: User,
    warning_actors: WarningActors,
):

    actors = warning_actors
    schedule = await schedule_for(container, actors.owner, actors.team.id)
    baseline, _ = await save_report(container, actors.owner, actors.team.id)
    await mark(container, schedule, baseline)
    schedule = await refresh(container, actors.owner, schedule.id)
    changed, _ = await save_report(container, actors.owner, actors.team.id, changed=True)
    await mark(container, schedule, changed)
    peer = bearer(await login_token(client, actors.peer.email, USER_PASSWORD))
    outsider = bearer(await login_token(client, actors.outsider.email, USER_PASSWORD))
    listed = await client.get("/api/warning/alerts", headers=peer)
    assert len(listed.json()["items"]) == 1
    alert = listed.json()["items"][0]
    assert alert["schedule_id"] == str(schedule.id) and alert["indicator_id"] is None
    assert (await client.get("/api/warning/alerts", headers=outsider)).json()["items"] == []
    assert (
        await client.post(f"/api/warning/alerts/{alert['id']}/ack", headers=outsider)
    ).status_code == 404
    assert (
        await client.post(f"/api/warning/alerts/{alert['id']}/ack", headers=peer)
    ).status_code == 200
    async with team_service(container) as service:
        await service.remove_member(admin, actors.team.id, actors.peer.id, CONTEXT)
    assert (await client.get("/api/warning/alerts", headers=peer)).json()["items"] == []


async def test_reconfiguration_resets_baseline_and_opt_out_preserves_report_runs(
    container: Container, user: User
):
    schedule = await schedule_for(container, user)
    report, _ = await save_report(container, user)
    await mark(container, schedule, report)
    async with container.session_factory() as session:
        schedule = await container.update_schedule(session).execute(
            user,
            schedule.id,
            ScheduleInput(
                name="Changed scope",
                template_id="ask",
                question="A different question?",
                notify_on_change=True,
            ),
            CONTEXT,
        )
    assert schedule.last_change is None
    changed, _ = await save_report(container, user, changed=True)
    await mark(container, schedule, changed)
    schedule = await refresh(container, user, schedule.id)
    assert schedule.last_change.status == "baseline"
    async with container.session_factory() as session:
        schedule = await container.update_schedule(session).execute(
            user,
            schedule.id,
            ScheduleInput(
                name="No alerts",
                template_id="ask",
                question="A different question?",
                notify_on_change=False,
            ),
            CONTEXT,
        )
    assert schedule.last_change is None
    normal, _ = await save_report(container, user)
    await mark(container, schedule, normal)
    schedule = await refresh(container, user, schedule.id)
    assert schedule.last_report_id == normal.id and schedule.last_change is None
    async with container.session_factory() as session:
        assert list(await session.scalars(select(AlertRow))) == []
