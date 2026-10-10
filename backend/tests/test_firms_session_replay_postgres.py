"""Refresh reuse must share the account authority boundary with credential work."""

import asyncio

import pytest
from sqlalchemy import text

from ase.adapters.persistence.firms_credentials import SqlFirmsCredentials
from ase.adapters.persistence.tokens import SqlRefreshTokenRepository
from ase.application.admin.firms_credentials import AdminFirmsCredentials
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRefreshToken, Unauthenticated
from firms_concurrency_helpers import invoke, observe_lock, settle
from firms_concurrency_helpers import settings as settings  # noqa: PLC0414
from team_helpers import CONTEXT
from test_firms_credentials import call, ready
from test_firms_credentials import probe as probe  # noqa: PLC0414
from test_saved_map_views import claims_for

pytestmark = pytest.mark.feed_catalogue


@pytest.mark.parametrize("boundary", ["commit", "disclosure"])
async def test_refresh_reuse_waits_for_credential_commit_or_disclosure(
    client, container, admin, probe, monkeypatch, boundary
):
    actor = await claims_for(client, container, admin)
    state = await ready(container, actor)
    old_secret = client.cookies.get("ase_refresh")
    async with container.session_factory() as session:
        await container.refresh(session).execute(old_secret, CONTEXT)
    entered, release = asyncio.Event(), asyncio.Event()
    replay_started, replay_done = asyncio.Event(), asyncio.Event()
    pids = {}
    read = SqlRefreshTokenRepository.family_is_active
    guard = AdminFirmsCredentials.guard
    reads = 0
    guards = 0

    async def guarded_release(service, claims):
        nonlocal guards
        guards += 1
        if guards == 2 and boundary == "commit":
            # Once commit releases the account lock, let replay finish before
            # the separate disclosure guard. It must refuse that disclosure.
            await asyncio.wait_for(replay_done.wait(), 10)
        await guard(service, claims)

    async def held_read(repository, *args, **kwargs):
        nonlocal reads
        result = await read(repository, *args, **kwargs)
        if asyncio.current_task().get_name() == "credential-work":
            reads += 1
            if reads == (2 if boundary == "commit" else 3):
                assert result is True
                entered.set()
                await asyncio.wait_for(release.wait(), 10)
        return result

    monkeypatch.setattr(SqlRefreshTokenRepository, "family_is_active", held_read)
    monkeypatch.setattr(AdminFirmsCredentials, "guard", guarded_release)

    async def replay():
        async with container.session_factory() as session:
            pids["replay"] = await session.scalar(text("SELECT pg_backend_pid()"))
            replay_started.set()
            with pytest.raises(InvalidRefreshToken):
                await container.refresh(session).execute(old_secret, CONTEXT)
        replay_done.set()

    work = asyncio.create_task(
        invoke(
            container,
            actor,
            "confirm",
            state.revision,
            state.test_generation,
            CONTEXT,
            pids=pids,
            label="work",
        ),
        name="credential-work",
    )
    revocation = None
    try:
        await asyncio.wait_for(entered.wait(), 10)
        revocation = asyncio.create_task(replay())
        await asyncio.wait_for(replay_started.wait(), 10)
        await observe_lock(container, pids["replay"])
        async with container.session_factory() as session:
            blockers = await session.scalar(
                text("SELECT pg_blocking_pids(:pid)"), {"pid": pids["replay"]}
            )
        assert pids["work"] in blockers and not revocation.done()
        assert len(set(pids.values())) == 2
        release.set()
        if boundary == "commit":
            with pytest.raises(Unauthenticated):
                await asyncio.wait_for(work, 10)
        else:
            # Revocation was waiting for this guarded release, so it can complete
            # only after the still-authorised result leaves the transaction.
            assert (await asyncio.wait_for(work, 10)).configured
        await asyncio.wait_for(revocation, 10)
        with pytest.raises(Unauthenticated):
            await call(container, actor, "get")
        async with container.session_factory() as session:
            row = await SqlFirmsCredentials(session).get()
            assert row.active_encrypted is not None and row.revision == state.revision + 1
            entries = await container.repositories(session).audit.list_before(None, 100)
            assert sum(entry.action is AuditAction.REFRESH_REUSE_DETECTED for entry in entries) == 1
    finally:
        await settle(release, work, revocation)
