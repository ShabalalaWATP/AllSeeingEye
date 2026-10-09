"""Subscription links resolve exact saved versions, never a regenerated latest report."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import delete, update

from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.domain.research_changes import ResearchChange
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from test_schedule_accept_baseline import _published


async def _history(client, container):
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


@pytest.mark.parametrize("unavailable", ["deleted", "denied", "wrong_report"])
async def test_unavailable_versions_are_not_replaced_with_latest(
    client, container, user, unavailable
):
    headers, schedule_id, _, report, first, second = await _history(client, container)
    other = await create_user(
        container, email="other-links@example.com", password="another-long-passphrase"
    )
    async with container.session_factory() as session:
        if unavailable == "deleted":
            await session.execute(
                delete(ReportVersionRow).where(ReportVersionRow.id.in_([first.id, second.id]))
            )
        elif unavailable == "denied":
            await session.execute(
                update(ReportRow).where(ReportRow.id == report.id).values(created_by=other.id)
            )
        else:
            await session.execute(
                update(ReportVersionRow)
                .where(ReportVersionRow.id.in_([first.id, second.id]))
                .values(report_id=uuid4())
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
