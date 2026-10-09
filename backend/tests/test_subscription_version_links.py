"""Subscription links resolve exact saved versions, never a regenerated latest report."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text, update

from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.api.subscription_projection import edition_outputs, schedule_outputs
from ase.domain.research_changes import ResearchChange
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from test_schedule_accept_baseline import _published


async def _history(client, container):
    if container.engine.dialect.name == "sqlite":
        # Keep these fixtures valid on PostgreSQL too, where FKs are always enforced.
        async with container.engine.connect() as connection:
            await connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            assert await connection.scalar(text("PRAGMA foreign_keys")) == 1
            await connection.commit()
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    schedule_id, edition, report, first = await _published(client, container, headers)
    second = replace(first, id=uuid4(), number=2)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.reports.add_version(replace(report, latest_version=2), second)
        await repos.reports.add_version(
            replace(report, latest_version=3), replace(first, id=uuid4(), number=3)
        )
        schedule = await repos.schedules.get(schedule_id)
        assert schedule is not None
        await repos.schedules.save(
            replace(
                schedule,
                last_report_id=report.id,
                last_version_id=second.id,
                last_change=ResearchChange(
                    status="unchanged",
                    report_id=report.id,
                    version_id=second.id,
                    previous_report_id=report.id,
                    previous_version_id=first.id,
                ),
            )
        )
        await session.commit()
    return headers, schedule_id, edition, report, first, second


async def test_history_and_schedule_links_stay_on_their_frozen_versions(client, container, user):
    headers, schedule_id, _, report, first, second = await _history(client, container)
    history = await client.get(f"/api/schedules/{schedule_id}/editions", headers=headers)
    assert history.status_code == 200
    item = history.json()["items"][0]
    assert item["version_id"] == str(first.id)
    assert item["version_number"] == 1
    listed = await client.get("/api/schedules", headers=headers)
    schedule = listed.json()["items"][0]
    assert schedule["last_version_id"] == str(second.id)
    assert schedule["last_version_number"] == 2
    assert schedule["previous_version_number"] == 1
    exact = await client.get(f"/api/reports/{report.id}?version=1", headers=headers)
    assert exact.status_code == 200
    assert exact.json()["version"]["number"] == 1
    paused = await client.post(f"/api/schedules/{schedule_id}/pause", headers=headers)
    assert paused.status_code == 200
    assert paused.json()["last_version_number"] == 2
    assert paused.json()["previous_version_number"] == 1


@pytest.mark.parametrize("unavailable", ["denied", "wrong_report"])
async def test_unavailable_versions_are_not_replaced_with_latest(
    client, container, user, unavailable
):
    headers, schedule_id, _, report, first, second = await _history(client, container)
    other = await create_user(
        container, email="other-links@example.com", password="another-long-passphrase"
    )
    async with container.session_factory() as session:
        if unavailable == "denied":
            await session.execute(
                update(ReportRow).where(ReportRow.id == report.id).values(created_by=other.id)
            )
        else:
            # Both reports exist and are visible; only their exact version pairs differ.
            alternate = replace(report, id=uuid4(), latest_version=3)
            await container.repositories(session).reports.add(
                alternate, replace(first, id=uuid4(), report_id=alternate.id, number=3)
            )
            await session.execute(
                update(ReportVersionRow)
                .where(ReportVersionRow.id.in_([first.id, second.id]))
                .values(report_id=alternate.id)
            )
        await session.commit()
    history = await client.get(f"/api/schedules/{schedule_id}/editions", headers=headers)
    assert history.status_code == 200
    assert history.json()["items"][0]["version_number"] is None
    listed = await client.get("/api/schedules", headers=headers)
    assert listed.json()["items"][0]["last_version_number"] is None
    assert listed.json()["items"][0]["previous_version_number"] is None
    assert (
        await client.get(f"/api/reports/{report.id}?version=1", headers=headers)
    ).status_code == 404


async def test_missing_version_references_are_not_replaced_with_latest(client, container, user):
    _, schedule_id, edition, report, _, _ = await _history(client, container)
    missing_current, missing_previous = uuid4(), uuid4()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        schedule = await repos.schedules.get(schedule_id)
        assert schedule is not None and schedule.last_change is not None
        assert await repos.reports.get_version(report.id, 3) is not None
        # PostgreSQL prevents deleting a pinned version. Project legacy missing IDs
        # without corrupting the retained graph or mocking the real SQL lookup.
        missing = replace(
            schedule,
            last_version_id=missing_current,
            last_change=replace(
                schedule.last_change,
                version_id=missing_current,
                previous_version_id=missing_previous,
            ),
        )
        projected = (await schedule_outputs(container, session, user, [missing]))[0]
        historical = (
            await edition_outputs(
                container, session, user, [replace(edition, version_id=missing_previous)]
            )
        )[0]
    assert projected.last_version_id == missing_current
    assert projected.last_version_number is None
    assert projected.previous_version_number is None
    assert historical.version_id == missing_previous
    assert historical.version_number is None


async def test_another_account_cannot_resolve_a_subscriptions_versions(client, container, user):
    _, schedule_id, _, _, _, _ = await _history(client, container)
    await create_user(container, email="outsider-links@example.com", password="long-passphrase")
    headers = bearer(await login_token(client, "outsider-links@example.com", "long-passphrase"))
    assert (await client.get("/api/schedules", headers=headers)).json()["items"] == []
    denied = await client.get(f"/api/schedules/{schedule_id}/editions", headers=headers)
    assert denied.status_code == 404


async def test_ambiguous_legacy_version_numbers_do_not_produce_a_link(client, container, user):
    headers, schedule_id, _, _, _, second = await _history(client, container)
    async with container.session_factory() as session:
        await session.execute(
            update(ReportVersionRow).where(ReportVersionRow.id == second.id).values(number=1)
        )
        await session.commit()
    history = await client.get(f"/api/schedules/{schedule_id}/editions", headers=headers)
    assert history.status_code == 200
    assert history.json()["items"][0]["version_number"] is None
    listed = await client.get("/api/schedules", headers=headers)
    assert listed.json()["items"][0]["last_version_number"] is None
    assert listed.json()["items"][0]["previous_version_number"] is None
