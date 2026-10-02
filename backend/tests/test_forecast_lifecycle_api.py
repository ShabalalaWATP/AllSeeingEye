"""Later evidence, immutable corrections, reminders and deliberate scoped exports."""

from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select

from ase.adapters.persistence.forecast_digest import due_review_count
from ase.adapters.persistence.ledger_models import ForecastReminderRow
from ase.domain.access import Visibility
from forecast_lifecycle_helpers import later_observation
from helpers import USER_PASSWORD, bearer, create_user, login_token
from test_report_ledgers_api import forecast_body, reviewed_fixture


async def create_forecast(client, container, user, early=False):
    report, _, revision, citation, path = await reviewed_fixture(container, user)
    body = forecast_body(revision, citation, container.clock.now())
    if early:
        body["review_at"] = (container.clock.now() + timedelta(days=1)).isoformat()
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(path + "/forecasts", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return report, path, body, response.json(), headers


async def test_resolution_requires_independent_later_observation_and_corrects_once(
    client, container, user
):
    _, path, _, ledger, headers = await create_forecast(client, container, user)
    target = path + "/" + ledger["anchor"]["id"] + "/reviews"
    review = {"state": "resolved", "outcome": True, "reason": "Observed the outcome."}
    assert (await client.post(target, headers=headers, json=review)).status_code == 422
    container.clock.advance(timedelta(days=3))
    evidence = await later_observation(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    review["outcome_evidence"] = [evidence]
    first = await client.post(target, headers=headers, json=review)
    assert first.status_code == 200, first.text
    decision = first.json()["history"]["decisions"][0]
    assert decision["outcome"] is True
    assert decision["actor_id"] == str(user.id)
    assert decision["evidence"][0]["passage_id"] == evidence["citation"]["excerpt_sha256"]
    assert (await client.post(target, headers=headers, json=review)).status_code == 409
    corrected = await client.post(
        target,
        headers=headers,
        json={
            **review,
            "outcome": False,
            "previous_decision_id": decision["id"],
            "corrects_decision_id": decision["id"],
            "reason": "Corrected interpretation of the observation.",
        },
    )
    assert corrected.status_code == 200, corrected.text
    assert [row["outcome"] for row in corrected.json()["history"]["decisions"]] == [True, False]
    query = {
        "since": ledger["anchor"]["created_at"],
        "until": container.clock.now().isoformat(),
        "personal": True,
    }
    counts = await client.get("/api/forecasts/counts", headers=headers, params=query)
    assert counts.status_code == 200, counts.text
    band = next(
        row for row in counts.json()["bands"] if row["likelihood"] == "realistic_possibility"
    )
    assert band["resolved_false"] == 1 and band["resolved_true"] == 0
    assert band["resolved_denominator"] == counts.json()["forecast_versions"] == 1
    assert (
        await client.get("/api/forecasts/counts", headers=headers, params=query)
    ).json() == counts.json()


async def test_outcome_scope_original_version_and_citation_cannot_be_forged(
    client, container, user
):
    _, path, body, ledger, _ = await create_forecast(client, container, user)
    container.clock.advance(timedelta(days=3))
    foreign = await create_user(
        container, email="foreign-outcome@example.com", password=USER_PASSWORD
    )
    evidence = await later_observation(container, foreign)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    target = path + "/" + ledger["anchor"]["id"] + "/reviews"
    review = {
        "state": "resolved",
        "outcome": True,
        "reason": "Review",
        "outcome_evidence": [evidence],
    }
    assert (await client.post(target, headers=headers, json=review)).status_code == 404
    original = {
        "report_id": ledger["anchor"]["report_id"],
        "version": 1,
        "claim_id": body["claim_id"],
        "claim_revision_id": body["claim_revision_id"],
        "citation": body["supporting"][0],
    }
    assert (
        await client.post(target, headers=headers, json={**review, "outcome_evidence": [original]})
    ).status_code == 422
    own = await later_observation(container, user)
    own["citation"]["excerpt_sha256"] = "0" * 64
    assert (
        await client.post(target, headers=headers, json={**review, "outcome_evidence": [own]})
    ).status_code == 422


async def test_supersession_is_atomic_and_original_band_is_counted_separately(
    client, container, user
):
    _, path, body, ledger, _ = await create_forecast(client, container, user)
    container.clock.advance(timedelta(hours=1))
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    target = path + "/" + ledger["anchor"]["id"] + "/supersessions"
    replacement = {**body, "likelihood": "likely"}
    command = {
        "expected_version_id": ledger["history"]["versions"][0]["version_id"],
        "reason": "Reconsidered assumptions",
        "replacement": replacement,
    }
    response = await client.post(target, headers=headers, json=command)
    assert response.status_code == 200, response.text
    assert response.json()["anchor"]["latest_ordinal"] == 3
    assert len(response.json()["history"]["versions"]) == 2
    assert response.json()["history"]["decisions"][0]["state"] == "superseded"
    assert (await client.post(target, headers=headers, json=command)).status_code == 409
    for token in ({"expected_version_id": command["expected_version_id"]}, {}):
        stale = await client.post(
            path + "/" + ledger["anchor"]["id"] + "/reviews",
            headers=headers,
            json={"state": "unresolved", "reason": "Stale review", **token},
        )
        assert stale.status_code == 409
    container.clock.advance(timedelta(seconds=1))
    result = await client.get(
        "/api/forecasts/counts",
        headers=headers,
        params={
            "since": ledger["anchor"]["created_at"],
            "until": container.clock.now().isoformat(),
        },
    )
    assert result.status_code == 200, result.text
    bands = {row["likelihood"]: row for row in result.json()["bands"]}
    assert bands["realistic_possibility"]["superseded"] == 1
    assert bands["likely"]["open"] == 1
    assert all(row["resolved_denominator"] == 0 for row in bands.values())


async def test_review_date_precedes_horizon_and_reminder_is_deduplicated(client, container, user):
    report, path, _, ledger, headers = await create_forecast(client, container, user, early=True)
    before = await client.get("/api/forecasts/watches?personal=true", headers=headers)
    assert before.status_code == 200, before.text
    assert before.json()["items"][0]["review_due"] is False
    container.clock.advance(timedelta(days=1, seconds=1))
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    first = await client.get("/api/forecasts/watches?personal=true", headers=headers)
    row = first.json()["items"][0]
    assert row["review_due"] is True and row["state"] == "open"
    assert row["reminded_at"]
    container.clock.advance(timedelta(seconds=2))
    assert (
        await client.get("/api/forecasts/watches?personal=true", headers=headers)
    ).json() == first.json()
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ForecastReminderRow)) == 1
        now = container.clock.now()
        assert await due_review_count(
            session, Visibility(user.id, True, ()), now - timedelta(hours=1), now
        ) == (1, False)
        assert await due_review_count(
            session, Visibility(user.id, False, ()), now, now + timedelta(days=1)
        ) == (0, False)
    selected = {"ledger_ids": [ledger["anchor"]["id"]]}
    export = await client.post(path + "/exports/forecasts", headers=headers, json=selected)
    assert export.status_code == 200 and len(export.json()) == 1
    assert export.headers["cache-control"] == "private, no-store"
    assert (
        await client.post(path + "/exports/forecasts", headers=headers, json={"ledger_ids": []})
    ).status_code == 422
    assert (
        await client.post(
            path.replace("/versions/1", "/versions/2") + "/exports/forecasts",
            headers=headers,
            json=selected,
        )
    ).status_code == 404
    async with container.session_factory() as session:
        await container.repositories(session).reports.delete(report.id)
        await session.commit()
        assert (
            await session.get(ForecastReminderRow, (UUID(row["version_id"]), container.clock.now()))
            is None
        )
        assert await session.scalar(select(func.count()).select_from(ForecastReminderRow)) == 0
