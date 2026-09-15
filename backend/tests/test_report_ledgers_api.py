"""Authorised forecast and indicator histories retain exact reviewed-claim anchors."""

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update

from ase.adapters.persistence.claims import SqlClaimRepository
from ase.adapters.persistence.ledger_models import ReportLedgerEntryRow, ReportLedgerHeadRow
from ase.adapters.persistence.report_ledgers import SqlReportLedgerRepository
from ase.application.reports.ledger_access import ReportLedgerAccess
from ase.domain.claim_revisions import ClaimReviewState
from helpers import USER_PASSWORD, bearer, create_user, login_token
from test_claim_repository import seed


async def reviewed_fixture(container, user):
    container.clock.advance(timedelta(days=7))
    report, version, proposal = await seed(container, user)
    reviewed = replace(
        proposal,
        id=uuid4(),
        number=2,
        previous_id=proposal.id,
        state=ClaimReviewState.REVIEWED,
        reason="Checked the frozen citation.",
        created_at=container.clock.now(),
    )
    async with container.session_factory() as session:
        assert await SqlClaimRepository(session).append(reviewed, proposal.id)
        await session.commit()
    citation = reviewed.citations[0]
    key = {"evidence_label": citation.label, "excerpt_sha256": citation.excerpt.sha256}
    path = f"/api/reports/{report.id}/versions/1/ledgers"
    return report, version, reviewed, key, path


def forecast_body(revision, citation, now):
    return {
        "claim_id": str(revision.claim_id),
        "claim_revision_id": str(revision.id),
        "horizon_end": (now + timedelta(days=2)).isoformat(),
        "review_at": (now + timedelta(days=2)).isoformat(),
        "criterion": {"description": "Whether the reported road remains open"},
        "likelihood": "realistic_possibility",
        "confidence": {
            "source_quality": "moderate",
            "corroboration": "low",
            "coverage": "low",
            "limitation": "Single frozen source",
        },
        "supporting": [citation],
    }


async def test_forecast_review_correction_and_exact_version_access(client, container, user):
    report, version, revision, citation, path = await reviewed_fixture(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    created = await client.post(
        path + "/forecasts",
        headers=headers,
        json=forecast_body(revision, citation, container.clock.now()),
    )
    assert created.status_code == 201, created.text
    ledger = created.json()
    assert ledger["anchor"]["report_version_id"] == str(version.id)
    assert ledger["history"]["versions"][0]["claim_version_id"] == str(revision.id)
    assert (
        ledger["history"]["versions"][0]["supporting"][0]["passage_id"]
        == citation["excerpt_sha256"]
    )
    ledger_id = ledger["anchor"]["id"]
    get = await client.get(path + "/" + ledger_id, headers=headers)
    assert get.status_code == 200 and get.json() == ledger
    assert get.headers["cache-control"] == "private, no-store"
    page = await client.get(path + "?limit=1", headers=headers)
    assert page.status_code == 200 and page.json()["total"] == 1
    assert (
        await client.get(
            path.replace("/versions/1", "/versions/2") + "/" + ledger_id, headers=headers
        )
    ).status_code == 404
    decision = {
        "state": "unresolved",
        "reason": "No later observation establishes the forecast outcome.",
        "evidence": [citation],
    }
    assert (
        await client.post(path + f"/{ledger_id}/reviews", headers=headers, json=decision)
    ).status_code == 422
    assert (
        await client.post(
            path + f"/{ledger_id}/reviews",
            headers=headers,
            json={**decision, "state": "resolved", "outcome": True},
        )
    ).status_code == 422
    container.clock.advance(timedelta(days=3))
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    first = await client.post(path + f"/{ledger_id}/reviews", headers=headers, json=decision)
    assert first.status_code == 200, first.text
    first_id = first.json()["history"]["decisions"][0]["id"]
    assert (
        await client.post(path + f"/{ledger_id}/reviews", headers=headers, json=decision)
    ).status_code == 409
    changed = await client.post(
        path + f"/{ledger_id}/reviews",
        headers=headers,
        json={
            **decision,
            "previous_decision_id": first_id,
            "corrects_decision_id": first_id,
            "reason": "Later review still found no unambiguous outcome evidence.",
        },
    )
    assert changed.status_code == 200, changed.text
    assert [row["state"] for row in changed.json()["history"]["decisions"]] == [
        "unresolved",
        "unresolved",
    ]
    assert (await client.get(path + "/" + ledger_id, headers=headers)).json()["history"][
        "decisions"
    ][0]["reason"] == decision["reason"]
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(report.id, 1)
        assert saved.markdown == version.markdown and saved.body == version.body


async def test_indicator_missing_data_never_becomes_false(client, container, user):
    _, version, revision, citation, path = await reviewed_fixture(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    now = container.clock.now()
    created = await client.post(
        path + "/indicators",
        headers=headers,
        json={
            "claim_id": str(revision.claim_id),
            "claim_revision_id": str(revision.id),
            "condition": "At least ten vehicles reported",
            "metric_id": "vehicles",
            "unit": "vehicles",
            "source_id": version.evidence[0].source_id,
            "source_capability": "Frozen report observation only",
            "expected_update_hours": 24,
            "source_citation": citation,
            "threshold": "10",
            "direction": "at_least",
        },
    )
    assert created.status_code == 201, created.text
    ledger_id = created.json()["anchor"]["id"]
    assert created.json()["anchor"]["source_reference"]["passage_id"] == citation["excerpt_sha256"]
    assert created.json()["history"]["readings"] == []
    missing = await client.post(
        path + f"/{ledger_id}/missing-readings",
        headers=headers,
        json={"observed_at": now.isoformat(), "missing_reason": "Source had no observation"},
    )
    assert missing.status_code == 200, missing.text
    async with container.session_factory() as session:
        ledger = await SqlReportLedgerRepository(session).get(UUID(ledger_id))
        assert ledger.history.evaluate_at(now).status.value == "unknown"
    assert len(missing.json()["history"]["readings"]) == 1
    async with container.session_factory() as session:
        await session.execute(
            update(ReportLedgerHeadRow)
            .where(ReportLedgerHeadRow.id == UUID(ledger_id))
            .values(source_excerpt_sha256="0" * 64)
        )
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(ValueError, match="anchor"):
            await SqlReportLedgerRepository(session).get(UUID(ledger_id))


async def test_foreign_scope_and_unreviewed_claim_are_rejected(client, container, user):
    _, _, revision, citation, path = await reviewed_fixture(container, user)
    stranger = await create_user(
        container, email="foreign-ledger@example.com", password=USER_PASSWORD
    )
    foreign = bearer(await login_token(client, stranger.email, USER_PASSWORD))
    owner = bearer(await login_token(client, user.email, USER_PASSWORD))
    body = forecast_body(revision, citation, container.clock.now())
    assert (await client.post(path + "/forecasts", headers=foreign, json=body)).status_code == 404
    wrong = {**body, "supporting": [{**citation, "excerpt_sha256": "0" * 64}]}
    assert (await client.post(path + "/forecasts", headers=owner, json=wrong)).status_code == 422
    assert (
        await client.post(
            path + "/forecasts", headers=owner, json={**body, "actor_id": str(user.id)}
        )
    ).status_code == 422


async def test_storage_detects_tampering_and_report_delete_removes_children(
    client, container, user
):
    report, _, revision, citation, path = await reviewed_fixture(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    created = await client.post(
        path + "/forecasts",
        headers=headers,
        json=forecast_body(revision, citation, container.clock.now()),
    )
    assert created.status_code == 201, created.text
    ledger_id = UUID(created.json()["anchor"]["id"])
    async with container.session_factory() as session:
        first = await session.scalar(
            select(ReportLedgerEntryRow).where(ReportLedgerEntryRow.ledger_id == ledger_id)
        )
        assert first is not None
        await session.execute(
            update(ReportLedgerEntryRow)
            .where(ReportLedgerEntryRow.id == first.id)
            .values(payload=first.payload.replace("realistic_possibility", "likely"))
        )
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(ValueError, match="integrity"):
            await SqlReportLedgerRepository(session).get(ledger_id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.delete(report.id)
        await session.commit()
    async with container.session_factory() as session:
        assert await session.get(ReportLedgerHeadRow, ledger_id) is None
        assert await session.scalar(select(ReportLedgerEntryRow)) is None


async def test_expiry_during_ledger_commit_blocks_private_response(
    client, container, user, monkeypatch
):
    _, _, revision, citation, path = await reviewed_fixture(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    created = await client.post(
        path + "/forecasts",
        headers=headers,
        json=forecast_body(revision, citation, container.clock.now()),
    )
    assert created.status_code == 201, created.text
    ledger_id = created.json()["anchor"]["id"]
    original = ReportLedgerAccess._commit

    async def expire_after_commit(self, claims):
        await original(self, claims)
        container.clock.advance(timedelta(hours=1))

    monkeypatch.setattr(ReportLedgerAccess, "_commit", expire_after_commit)
    response = await client.get(path + "/" + ledger_id, headers=headers)
    assert response.status_code == 401
    assert ledger_id not in response.text


async def test_forecast_head_only_claim_revision_tampering_is_detected(client, container, user):
    _, _, revision, citation, path = await reviewed_fixture(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    created = await client.post(
        path + "/forecasts",
        headers=headers,
        json=forecast_body(revision, citation, container.clock.now()),
    )
    assert created.status_code == 201, created.text
    ledger_id = UUID(created.json()["anchor"]["id"])
    assert revision.previous_id is not None
    async with container.session_factory() as session:
        await session.execute(
            update(ReportLedgerHeadRow)
            .where(ReportLedgerHeadRow.id == ledger_id)
            .values(claim_revision_id=revision.previous_id)
        )
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(ValueError, match="anchor"):
            await SqlReportLedgerRepository(session).get(ledger_id)
