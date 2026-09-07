"""Routed claim generation persists provenance, accounts for cost and rechecks access."""

import asyncio
import json
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Request

from ase.api.claim_run import run_claim_generation
from ase.domain.errors import RateLimited, Unauthenticated
from ase.domain.llm import LlmResult
from helpers import USER_PASSWORD, bearer, login_token
from production_integration_helpers import production_job
from team_helpers import CONTEXT
from test_claim_repository import seed
from test_saved_map_views import claims_for


async def setup_model(container, user):
    profile = production_job(user, container.cipher).profile
    async with container.session_factory() as session:
        await container.repositories(session).llm_profiles.add(profile)
        await session.commit()
    return profile


def output_for(version):
    item = version.evidence[0]
    return json.dumps(
        {
            "claims": [
                {
                    "statement": "The source reports this observation.",
                    "kind": "reported_fact",
                    "citations": [
                        {
                            "label": item.label,
                            "relation": "supporting",
                            "field": "title",
                            "text": item.title,
                        }
                    ],
                    "unresolved_conflicts": [],
                }
            ]
        }
    )


async def test_http_generation_retains_routed_provenance(client, container, user, monkeypatch):
    profile = await setup_model(container, user)
    report, version, _ = await seed(container, user)
    gateway = AsyncMock()
    gateway.complete.return_value = LlmResult(output_for(version), "returned-model", 5, 10, 20)
    monkeypatch.setattr(container, "llm", gateway)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(
        "/api/claims/generate",
        headers=headers,
        json={
            "report_id": str(report.id),
            "version_number": 1,
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    result = response.json()
    assert result["status"] == "completed" and len(result["items"]) == 1
    item = result["items"][0]
    assert item["state"] == "proposed"
    assert item["model_origin"]["profile_id"] == str(profile.id)
    assert item["model_origin"]["returned_model"] == "returned-model"
    assert "test-key" not in response.text
    async with container.session_factory() as session:
        usage = await container.repositories(session).llm_usage.list_recent(10)
        assert usage[0].purpose == "claim_proposals" and usage[0].ok
        assert usage[0].completion_tokens == 20


@pytest.mark.parametrize("output,status", [("not JSON", "invalid"), ('{"claims":[]}', "empty")])
async def test_non_claim_outcomes_have_usage_and_no_claims(client, container, user, output, status):
    await setup_model(container, user)
    actor = await claims_for(client, container, user)
    report, _, _ = await seed(container, user)
    async with container.session_factory() as session:
        service = container.generate_claims(session)
        service.gateway = AsyncMock()
        service.gateway.complete.return_value = LlmResult(output, "actual", 5, 10, 20)
        result = await service.execute(actor, report.id, 1, CONTEXT)
        assert result.status == status and not result.items
        assert (await container.report_claims(session).list(actor, report.id, 1))[1] == 1
        usage = await container.repositories(session).llm_usage.list_recent(10)
        assert usage[0].ok == (status == "empty")


async def test_no_database_transaction_during_model_and_revocation_rechecked(
    client, container, user
):
    await setup_model(container, user)
    actor = await claims_for(client, container, user)
    report, version, _ = await seed(container, user)
    async with container.session_factory() as session:
        service = container.generate_claims(session)

        async def complete(*args):
            assert not session.in_transaction()
            # Simulate fresh-session validation discovering a revocation after the call.
            service.claims.persist_proposals = AsyncMock(side_effect=Unauthenticated())
            return LlmResult(output_for(version), "actual", 5, 10, 20)

        service.gateway = AsyncMock()
        service.gateway.complete.side_effect = complete
        with pytest.raises(Unauthenticated):
            await service.execute(actor, report.id, 1, CONTEXT)
        usage = await container.repositories(session).llm_usage.list_recent(10)
        assert len(usage) == 1
        assert (await container.report_claims(session).list(actor, report.id, 1))[1] == 1


async def test_rate_limit_and_stale_session_make_no_provider_call(client, container, user):
    await setup_model(container, user)
    actor = await claims_for(client, container, user)
    report, _, _ = await seed(container, user)
    async with container.session_factory() as session:
        service = container.generate_claims(session)
        service.gateway = AsyncMock()
        with pytest.raises(Unauthenticated):
            await service.execute(
                replace(actor, security_version=actor.security_version + 1), report.id, 1, CONTEXT
            )
        await session.rollback()
        for _ in range(2):
            container.limiter.hit(f"claims:report:{report.id}:1", 2, 3600)
        with pytest.raises(RateLimited):
            await service.execute(actor, report.id, 1, CONTEXT)
        service.gateway.complete.assert_not_called()


async def test_disconnect_cancels_model_and_records_unknown_cost(client, container, user):
    await setup_model(container, user)
    actor = await claims_for(client, container, user)
    report, _, _ = await seed(container, user)
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def receive():
        await started.wait()
        return {"type": "http.disconnect"}

    async def complete(*args):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    request = Request({"type": "http"}, receive)
    async with container.session_factory() as session:
        service = container.generate_claims(session)
        service.gateway = AsyncMock()
        service.gateway.complete.side_effect = complete
        with pytest.raises(HTTPException) as error:
            await run_claim_generation(request, service.execute(actor, report.id, 1, CONTEXT))
        assert error.value.status_code == 499 and stopped.is_set()
        assert not session.in_transaction()
        usage = await container.repositories(session).llm_usage.list_recent(10)
        assert len(usage) == 1 and usage[0].error == "cancelled"
        assert usage[0].prompt_tokens is None and usage[0].completion_tokens is None
        assert (await container.report_claims(session).list(actor, report.id, 1))[1] == 1
