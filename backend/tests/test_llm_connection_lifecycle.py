"""Controlled model pauses prove post-network proof/session race handling."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient

from ase.api.schemas_llm import LlmConnectionIn, LlmProfileIn
from ase.application.dto import RequestContext
from ase.container import Container
from ase.domain.errors import Unauthenticated
from ase.domain.llm import LlmRequest, LlmResult
from ase.domain.users import Role, User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, FakeClock, bearer, csrf_headers, login_token
from test_llm import FakeGateway
from test_llm_connections import DRAFT, ROOT, activation, draft, proof


class PausedModel:
    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = 0

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        self.calls += 1
        if self.calls == 1:
            self.entered.set()
            await self.release.wait()
            return LlmResult('{"ok":true}', model, 1)
        return LlmResult('{"ok":false}', model, 1)

    async def list_models(self, base_url: str, api_key: str) -> tuple[str, ...]:
        self.entered.set()
        await self.release.wait()
        return ("model",)


async def test_older_success_cannot_replace_a_newer_failed_test(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    profile = await draft(client, headers)
    model = PausedModel()
    container.llm = model
    path = f"{ROOT}/profiles/{profile['id']}/test"
    older = asyncio.create_task(client.post(path, headers=headers))
    await asyncio.wait_for(model.entered.wait(), 3)
    newer = await client.post(path, headers=headers)
    assert newer.status_code == 200 and not newer.json()["ok"]
    model.release.set()
    stale = await asyncio.wait_for(older, 3)
    assert stale.status_code == 422 and "superseded" in stale.text
    async with container.session_factory() as session:
        saved = await container.repositories(session).llm_profiles.get(UUID(profile["id"]))
        assert saved is not None and saved.test_generation == 2 and not saved.is_tested


async def test_in_flight_probe_cannot_certify_an_edited_revision(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    profile = await draft(client, headers)
    model = PausedModel()
    container.llm = model
    older = asyncio.create_task(
        client.post(f"{ROOT}/profiles/{profile['id']}/test", headers=headers)
    )
    await asyncio.wait_for(model.entered.wait(), 3)
    changed = await client.put(
        f"{ROOT}/profiles/{profile['id']}",
        headers=headers,
        json={**DRAFT, "model": "replacement", "api_key": "replacement-key"},
    )
    assert changed.status_code == 200
    model.release.set()
    assert (await asyncio.wait_for(older, 3)).status_code == 422
    listed = (await client.get(f"{ROOT}/profiles", headers=headers)).json()["items"][0]
    assert listed["model"] == "replacement" and not listed["is_tested"]


@pytest.mark.parametrize("operation", ["test", "models"])
@pytest.mark.parametrize(
    "transition", ["logout", "logout_new_login", "expiry", "demotion", "deactivation"]
)
async def test_network_result_rechecks_original_session_and_current_admin(
    client: AsyncClient,
    container: Container,
    admin: User,
    clock: FakeClock,
    operation: str,
    transition: str,
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    profile = await draft(client, headers)
    model = PausedModel()
    container.llm = model
    container.model_discovery = model
    path = f"{ROOT}/profiles/{profile['id']}/{operation}"
    pending = asyncio.create_task(
        client.request("POST" if operation == "test" else "GET", path, headers=headers)
    )
    await asyncio.wait_for(model.entered.wait(), 3)
    if transition.startswith("logout"):
        assert (
            await client.post("/api/auth/logout", headers=csrf_headers(client))
        ).status_code == 204
        if transition == "logout_new_login":
            await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    elif transition == "expiry":
        clock.advance(timedelta(minutes=16))
    else:
        async with container.session_factory() as session:
            r = container.repositories(session)
            current = await r.users.get_by_id(admin.id)
            assert current is not None
            if transition == "demotion":
                current.role = Role.USER  # Even without a version bump, current role governs.
            else:
                current.is_active = False
            await r.users.save(current)
            await r.uow.commit()
    model.release.set()
    result = await asyncio.wait_for(pending, 3)
    assert result.status_code == (403 if transition == "demotion" else 401), result.text
    async with container.session_factory() as session:
        r = container.repositories(session)
        saved = await r.llm_profiles.get(UUID(profile["id"]))
        assert saved is not None and not saved.is_tested
        assert not await r.llm_usage.list_recent(10)


async def test_cancellation_leaves_no_proof_and_releases_mutation_guard(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    profile = await draft(client, headers)
    model = PausedModel()
    container.llm = model
    pending = asyncio.create_task(
        client.post(f"{ROOT}/profiles/{profile['id']}/test", headers=headers)
    )
    await asyncio.wait_for(model.entered.wait(), 3)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    container.llm = FakeGateway()
    assert (await proof(client, headers, profile))["ok"]


@pytest.mark.parametrize("operation", ["create", "update", "delete", "activate", "reset"])
async def test_original_session_guard_failure_rolls_back_mutations(
    client: AsyncClient, container: Container, admin: User, operation: str
) -> None:

    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    container.llm = FakeGateway()
    profile = await draft(client, headers)
    receipt = await proof(client, headers, profile)
    callback_invoked = False

    async def expired() -> None:
        nonlocal callback_invoked
        callback_invoked = True
        raise Unauthenticated()

    context = RequestContext(None, None)
    async with container.session_factory() as session:
        # First administrator sign-in enrols MFA and changes the credential version.
        # Use that current actor so only the final session callback rejects this write.
        current_admin = await container.repositories(session).users.get_by_id(admin.id)
        assert current_admin is not None
        admin = current_admin
        with pytest.raises(Unauthenticated):
            if operation == "create":
                data = LlmProfileIn.model_validate({**DRAFT, "name": "Rejected"}).to_input()
                await container.create_llm_profile(session).execute(
                    admin, data, context, before_save=expired
                )
            elif operation == "update":
                data = LlmProfileIn.model_validate(DRAFT).to_input()
                await container.update_llm_profile(session).execute(
                    admin, UUID(profile["id"]), data, context, before_save=expired
                )
            elif operation == "delete":
                await container.delete_llm_profile(session).execute(
                    admin, UUID(profile["id"]), context, before_save=expired
                )
            elif operation == "activate":
                binding = LlmConnectionIn.model_validate(activation(profile, receipt)).to_input()
                await container.llm_connections(session).activate(
                    admin, binding, context, before_save=expired
                )
            else:
                # Reset uses the same final callback; set up the exact binding through the API.
                binding = LlmConnectionIn.model_validate(activation(profile, receipt)).to_input()
                active = await container.llm_connections(session).activate(admin, binding, context)
                team = await client.post("/api/teams", headers=headers, json={"name": "Reset team"})
                team_id = UUID(team.json()["id"])
                active = await container.llm_connections(session).activate(
                    admin, replace(binding, team_id=team_id), context
                )
                await container.llm_connections(session).reset_team(
                    admin, team_id, active.revision, context, before_save=expired
                )
        assert callback_invoked
        await session.rollback()
    async with container.session_factory() as session:
        r = container.repositories(session)
        profiles = await r.llm_profiles.list_all()
        assert len(profiles) == 1 and profiles[0].revision == 1
        bindings = await r.llm_bindings.list_all()
        assert len(bindings) == (2 if operation == "reset" else 0)
