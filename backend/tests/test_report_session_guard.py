"""Original HTTP session authority must still hold when generation starts saving."""

import asyncio
import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from ase.adapters.persistence.models import LlmUsageRow, ReportRow, ReportVersionRow
from ase.api.session_guard import validate_request_session
from ase.application.ports.feeds import EventQuery
from ase.domain.errors import Unauthenticated
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_helpers import PROFILE, ScriptedGateway, filled_store, good_body


@pytest.mark.parametrize("reason", ["revoke", "expiry", "new_session"])
@pytest.mark.parametrize("mutation", ["create", "regenerate"])
async def test_original_session_must_survive_blocked_model_until_save(
    client, container, admin, user, clock, reason, mutation
):
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    await client.post("/api/admin/llm/profiles", json=PROFILE, headers=bearer(admin_token))
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    claims = container.issuer.verify(token)
    container.store.upsert(tuple(filled_store().query(EventQuery(limit=10))))
    url, payload = "/api/reports", {"template": "intsum"}
    if mutation == "regenerate":
        container.llm = ScriptedGateway(json.dumps(good_body()))
        first = await client.post(url, json=payload, headers=bearer(token))
        assert first.status_code == 201
        url = f"/api/reports/{first.json()['report']['id']}/versions"
    async with container.session_factory() as session:
        baseline = await session.scalar(select(func.count()).select_from(LlmUsageRow))
    if reason == "expiry":
        clock.advance(timedelta(minutes=14))
    entered, release = asyncio.Event(), asyncio.Event()

    class WaitingGateway(ScriptedGateway):
        async def complete(self, *args):
            entered.set()
            await release.wait()
            return await super().complete(*args)

    container.llm = WaitingGateway(json.dumps(good_body()))
    # Absence of the optional telemetry header must not disable session checks.
    headers = bearer(token)
    if reason == "new_session":
        headers = {**headers, "X-Research-Run-ID": str(uuid4())}
    task = asyncio.create_task(client.post(url, json=payload, headers=headers))
    await asyncio.wait_for(entered.wait(), 3)
    if reason == "expiry":
        clock.advance(timedelta(minutes=2))
    else:
        async with container.session_factory() as session:
            repos = container.repositories(session)
            await repos.refresh_tokens.revoke_family(claims.family_id, clock.now())
            await repos.uow.commit()
        if reason == "new_session":
            new_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
            assert (await client.get("/api/reports", headers=bearer(new_token))).status_code == 200
    assert (await client.get("/api/reports", headers=bearer(token))).status_code == 401
    release.set()
    response = await asyncio.wait_for(task, 5)
    assert response.status_code == 401, response.text
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(LlmUsageRow)) == baseline
        assert await session.scalar(select(func.count()).select_from(ReportRow)) == (
            mutation == "regenerate"
        )
        assert await session.scalar(select(func.count()).select_from(ReportVersionRow)) == (
            mutation == "regenerate"
        )


async def test_original_token_expiry_is_checked_after_fresh_session_closes(
    client, container, user, clock, monkeypatch
):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    claims = container.issuer.verify(token)
    clock.advance(timedelta(minutes=14, seconds=59))
    context = AsyncMock()

    async def close(*args):
        clock.advance(timedelta(seconds=2))

    context.__aexit__.side_effect = close
    check = AsyncMock(return_value=user)
    monkeypatch.setattr("ase.api.session_guard.validate_current_session", check)
    fake = SimpleNamespace(
        session_factory=lambda: context,
        clock=clock,
        repositories=lambda _: SimpleNamespace(users=object(), refresh_tokens=object()),
    )
    with pytest.raises(Unauthenticated):
        await validate_request_session(fake, claims)
    assert context.__aexit__.await_count == check.await_count == 1
