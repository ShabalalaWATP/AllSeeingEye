"""Forecast projections and writes obey current scope after listing."""

from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, update

from ase.adapters.persistence.claim_models import ClaimRow
from ase.adapters.persistence.forecast_digest import due_review_count
from ase.adapters.persistence.ledger_models import ForecastReminderRow, ReportLedgerHeadRow
from ase.adapters.persistence.models import ReportRow
from ase.domain.access import Visibility
from helpers import USER_PASSWORD, bearer, create_user, login_token
from team_helpers import CONTEXT, team_service
from test_forecast_lifecycle_api import create_forecast
from test_report_team_scope import team_for


async def test_archived_team_is_readable_but_mutation_and_reminders_are_blocked(
    client, container, user, admin
):
    report, path, _, ledger, _ = await create_forecast(client, container, user, early=True)
    team = await team_for(container, admin, user)
    async with container.session_factory() as session:
        await session.execute(
            update(ReportRow).where(ReportRow.id == report.id).values(team_id=team.id)
        )
        await session.execute(
            update(ClaimRow)
            .where(ClaimRow.id == UUID(ledger["anchor"]["claim_id"]))
            .values(team_id=team.id)
        )
        await session.execute(
            update(ReportLedgerHeadRow)
            .where(ReportLedgerHeadRow.id == UUID(ledger["anchor"]["id"]))
            .values(team_id=team.id)
        )
        await session.commit()
    container.clock.advance(timedelta(days=3))
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    assert (await client.get(path, headers=headers)).status_code == 200
    async with team_service(container) as service:
        await service.update(admin, team.id, name=None, is_active=False, context=CONTEXT)
    watched = await client.get(
        "/api/forecasts/watches", headers=headers, params={"team_id": str(team.id)}
    )
    assert watched.status_code == 200, watched.text
    assert watched.json()["items"][0]["review_due"] is True
    assert watched.json()["items"][0]["reminded_at"] is None
    mutation = await client.post(
        path + "/" + ledger["anchor"]["id"] + "/reviews",
        headers=headers,
        json={"state": "unresolved", "reason": "Unable to establish outcome"},
    )
    assert mutation.status_code == 403, mutation.text
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ForecastReminderRow)) == 0
        assert await due_review_count(
            session,
            Visibility(user.id, False, (team.id,)),
            container.clock.now() - timedelta(days=7),
            container.clock.now(),
        ) == (0, False)
    async with team_service(container) as service:
        await service.update(admin, team.id, name=None, is_active=True, context=CONTEXT)
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    assert (await client.get(path, headers=headers)).status_code == 404
    assert (
        await client.post(
            path + "/exports/forecasts",
            headers=headers,
            json={"ledger_ids": [ledger["anchor"]["id"]]},
        )
    ).status_code == 404
    for endpoint in ("watches", "counts"):
        params = {
            "team_id": str(team.id),
            "since": ledger["anchor"]["created_at"],
            "until": container.clock.now().isoformat(),
        }
        assert (
            await client.get("/api/forecasts/" + endpoint, headers=headers, params=params)
        ).status_code == 404


async def test_personal_forecast_never_leaks_through_counts_or_watch_total(client, container, user):
    _, _, _, ledger, _ = await create_forecast(client, container, user)
    stranger = await create_user(
        container, email="forecast-stranger@example.com", password=USER_PASSWORD
    )
    headers = bearer(await login_token(client, stranger.email, USER_PASSWORD))
    container.clock.advance(timedelta(seconds=1))
    params = {"since": ledger["anchor"]["created_at"], "until": container.clock.now().isoformat()}
    counts = await client.get("/api/forecasts/counts", headers=headers, params=params)
    assert counts.status_code == 200 and counts.json()["forecast_versions"] == 0
    assert all(row["resolved_denominator"] == 0 for row in counts.json()["bands"])
    watched = await client.get("/api/forecasts/watches", headers=headers)
    assert watched.status_code == 200 and watched.json()["total"] == 0
    async with container.session_factory() as session:
        # An administrator's recipient digest does not inherit cross-personal read authority.
        assert await due_review_count(
            session,
            Visibility(stranger.id, True, ()),
            container.clock.now(),
            container.clock.now() + timedelta(days=5),
        ) == (0, False)
    invalid = await client.get(
        "/api/forecasts/counts", headers=headers, params={**params, "team_id": str(uuid4())}
    )
    assert invalid.status_code == 404


async def test_issue_window_is_half_open_and_invalid_windows_are_rejected(client, container, user):
    _, _, _, _, headers = await create_forecast(client, container, user)
    issue = container.clock.now()
    empty = await client.get(
        "/api/forecasts/counts",
        headers=headers,
        params={"since": (issue - timedelta(days=1)).isoformat(), "until": issue.isoformat()},
    )
    assert empty.status_code == 200 and empty.json()["forecast_versions"] == 0
    for since, until in (
        (issue.isoformat(), issue.isoformat()),
        ("2026-01-01T00:00:00", "2027-01-01T00:00:00"),
    ):
        response = await client.get(
            "/api/forecasts/counts", headers=headers, params={"since": since, "until": until}
        )
        assert response.status_code == 422
