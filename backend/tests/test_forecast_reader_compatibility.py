"""Citation verdicts and team copies never rewrite or transfer a personal forecast."""

from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select

from ase.adapters.persistence.claim_models import ClaimRow
from ase.adapters.persistence.ledger_models import ForecastReminderRow, ReportLedgerHeadRow
from helpers import USER_PASSWORD, bearer, create_user, login_token
from team_copy_helpers import team_with
from test_claim_repository import seed
from test_forecast_lifecycle_api import create_forecast
from test_report_ledgers_api import forecast_body


async def test_citation_verdict_does_not_review_a_proposed_forecast_claim(client, container, user):
    record, _, proposal = await seed(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    verdict = await client.post(
        f"/api/reports/{record.id}/versions/1/citation-verdicts",
        headers=headers,
        json={
            "judgement_id": "KJ1",
            "label": "E1",
            "relation": "supporting",
            "verdict": "supports",
        },
    )
    assert verdict.status_code == 201, verdict.text
    citation = proposal.citations[0]
    key = {"evidence_label": citation.label, "excerpt_sha256": citation.excerpt.sha256}
    forecast = await client.post(
        f"/api/reports/{record.id}/versions/1/ledgers/forecasts",
        headers=headers,
        json=forecast_body(proposal, key, container.clock.now()),
    )
    assert forecast.status_code == 422, forecast.text
    assert "Review this exact claim revision" in forecast.text


async def test_citation_verdict_does_not_change_an_issued_forecast(client, container, user):
    report, path, _, ledger, headers = await create_forecast(client, container, user)
    result = await client.post(
        f"/api/reports/{report.id}/versions/1/citation-verdicts",
        headers=headers,
        json={
            "judgement_id": "KJ1",
            "label": "E1",
            "relation": "supporting",
            "verdict": "does_not_support",
        },
    )
    assert result.status_code == 201, result.text
    retained = await client.get(path + "/" + ledger["anchor"]["id"], headers=headers)
    assert retained.status_code == 200 and retained.json() == ledger


async def test_team_copy_keeps_personal_forecasts_claims_and_reminders_in_their_scope(
    client, container, user, admin
):
    report, path, body, ledger, _ = await create_forecast(client, container, user, early=True)
    peer = await create_user(
        container, email="forecast-copy-peer@example.com", password=USER_PASSWORD
    )
    team = await team_with(container, admin, user, peer)
    container.clock.advance(timedelta(days=3))
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    watched = await client.get("/api/forecasts/watches", params={"personal": True}, headers=headers)
    assert watched.status_code == 200 and watched.json()["items"][0]["reminded_at"] is not None
    copied = await client.post(
        f"/api/reports/{report.id}/versions/1/team-copies",
        headers=headers,
        json={"team_id": str(team.id), "disclosed_evidence_labels": []},
    )
    assert copied.status_code == 201, copied.text
    copy_id = copied.json()["report_id"]
    reader = bearer(await login_token(client, peer.email, USER_PASSWORD))
    copy_path = f"/api/reports/{copy_id}/versions/1/ledgers"
    listed = await client.get(copy_path, headers=reader)
    assert listed.status_code == 200 and listed.json()["total"] == 0
    assert (await client.get(path, headers=reader)).status_code == 404
    # Even the personal owner may not bind an original personal claim to the team copy.
    forged = await client.post(copy_path + "/forecasts", headers=headers, json=body)
    assert forged.status_code == 422, forged.text
    assert "same personal or team scope" in forged.text
    assert (await client.get(copy_path, headers=reader)).json()["total"] == 0
    team_watches = await client.get(
        "/api/forecasts/watches", headers=reader, params={"team_id": str(team.id)}
    )
    assert team_watches.status_code == 200 and team_watches.json()["total"] == 0
    original = (await client.get(f"/api/reports/{report.id}?version=1", headers=headers)).json()
    copy = (await client.get(f"/api/reports/{copy_id}?version=1", headers=reader)).json()
    assert copy["version"]["created_at"] == original["version"]["created_at"]
    assert copy["version"]["evidence"] == original["version"]["evidence"]
    async with container.session_factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ClaimRow)
                .where(ClaimRow.report_id == UUID(copy_id))
            )
            == 0
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ReportLedgerHeadRow)
                .where(ReportLedgerHeadRow.report_id == UUID(copy_id))
            )
            == 0
        )
        reminders = list(await session.scalars(select(ForecastReminderRow)))
    assert len(reminders) == 1 and str(reminders[0].ledger_id) == ledger["anchor"]["id"]
