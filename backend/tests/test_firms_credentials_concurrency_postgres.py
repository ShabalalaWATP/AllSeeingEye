"""Independent PostgreSQL transactions verify FIRMS CAS and guarded live publication.

These tests create the current schema through metadata, not Alembic migrations.
"""

import asyncio

import pytest
from sqlalchemy import text

from ase.adapters.feeds.firms import SPEC, FirmsConnector
from ase.adapters.persistence.firms_credentials import SqlFirmsCredentials
from ase.application.admin.firms_credentials import AdminFirmsCredentials
from ase.domain.errors import Conflict, Unauthenticated
from ase.domain.users import Role
from feeds_helpers import make_event
from firms_concurrency_helpers import invoke, observe_lock, settle, watch_lock
from firms_concurrency_helpers import settings as settings  # noqa: PLC0414
from helpers import ADMIN_PASSWORD, create_user
from team_helpers import CONTEXT
from test_firms_credentials import KEY, call, ready
from test_firms_credentials import probe as probe  # noqa: PLC0414
from test_firms_runtime import active, connector
from test_saved_map_views import claims_for


@pytest.mark.parametrize("competitor", ["confirm", "clear"])
async def test_stale_confirmation_or_clear_waits_then_fails_current_revision_cas(
    client, container, admin, probe, monkeypatch, competitor
):
    actor = await claims_for(client, container, admin)
    state = await ready(container, actor)
    entered, release, waiting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    pids = {}
    original = SqlFirmsCredentials.save

    async def save(repository, row):
        await original(repository, row)
        if asyncio.current_task().get_name() == "first-confirm":
            entered.set()
            await asyncio.wait_for(release.wait(), 10)

    monkeypatch.setattr(SqlFirmsCredentials, "save", save)
    watch_lock(monkeypatch, "stale-write", pids, waiting)
    first = asyncio.create_task(
        invoke(
            container,
            actor,
            "confirm",
            state.revision,
            state.test_generation,
            CONTEXT,
            pids=pids,
            label="first",
        ),
        name="first-confirm",
    )
    other = None
    try:
        await asyncio.wait_for(entered.wait(), 10)
        args = (
            (state.revision, state.test_generation, CONTEXT)
            if competitor == "confirm"
            else (
                state.revision,
                CONTEXT,
            )
        )
        other = asyncio.create_task(invoke(container, actor, competitor, *args), name="stale-write")
        await asyncio.wait_for(waiting.wait(), 10)
        await observe_lock(container, pids["stale-write"])
        assert len(set(pids.values())) == 2 and not other.done()
        release.set()
        confirmed = await asyncio.wait_for(first, 10)
        with pytest.raises(Conflict):
            await asyncio.wait_for(other, 10)
        assert confirmed.active_revision == 1 and confirmed.revision == state.revision + 1
        assert (await call(container, actor, "get")).configured
    finally:
        await settle(release, first, other)


async def test_later_test_generation_wins_while_earlier_probe_is_still_running(
    client, container, admin, probe
):
    actor = await claims_for(client, container, admin)
    state = await call(container, actor, "draft", KEY, 0, CONTEXT)
    started, release = asyncio.Event(), asyncio.Event()
    pids = {}
    count = 0

    async def test(*args):
        nonlocal count
        count += 1
        if count == 1:
            started.set()
            await asyncio.wait_for(release.wait(), 10)
        return 3

    probe.side_effect = test
    first = asyncio.create_task(
        invoke(container, actor, "test", state.revision, CONTEXT, pids=pids, label="first")
    )
    try:
        await asyncio.wait_for(started.wait(), 10)
        latest = await invoke(
            container, actor, "test", state.revision, CONTEXT, pids=pids, label="second"
        )
        assert len(set(pids.values())) == 2
        release.set()
        with pytest.raises(Conflict):
            await asyncio.wait_for(first, 10)
        assert latest.ok and latest.status.test_generation == 2
        current = await call(container, actor, "get")
        assert current.test_ok and current.test_generation == 2 and not current.configured
    finally:
        await settle(release, first)


@pytest.mark.parametrize("method", ["get", "confirm"])
async def test_real_logout_during_late_preparation_denies_release_and_rolls_back_activation(
    client, container, admin, probe, monkeypatch, method
):
    actor = await claims_for(client, container, admin)
    state = await ready(container, actor)
    refresh = client.cookies.get("ase_refresh")
    entered, release = asyncio.Event(), asyncio.Event()
    pids = {}
    original = AdminFirmsCredentials.finish

    async def finish(service, claims):
        entered.set()
        await asyncio.wait_for(release.wait(), 10)
        await original(service, claims)

    monkeypatch.setattr(AdminFirmsCredentials, "finish", finish)
    args = (state.revision, state.test_generation, CONTEXT) if method == "confirm" else ()
    work = asyncio.create_task(invoke(container, actor, method, *args, pids=pids, label="work"))
    try:
        await asyncio.wait_for(entered.wait(), 10)
        async with container.session_factory() as session:
            pids["logout"] = await session.scalar(text("SELECT pg_backend_pid()"))
            await asyncio.wait_for(container.logout(session).execute(refresh, CONTEXT), 10)
        assert len(set(pids.values())) == 2
        release.set()
        with pytest.raises(Unauthenticated):
            await asyncio.wait_for(work, 10)
        async with container.session_factory() as session:
            row = await SqlFirmsCredentials(session).get()
            assert row.active_encrypted is None and row.revision == state.revision
    finally:
        await settle(release, work)


async def test_real_admin_revocation_during_probe_prevents_test_proof(
    client, container, admin, probe
):
    authority = await create_user(
        container, email="firms-other-admin@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    actor = await claims_for(client, container, admin)
    state = await call(container, actor, "draft", KEY, 0, CONTEXT)
    started, release = asyncio.Event(), asyncio.Event()
    pids = {}

    async def test(*args):
        started.set()
        await asyncio.wait_for(release.wait(), 10)
        return 3

    probe.side_effect = test
    work = asyncio.create_task(
        invoke(container, actor, "test", state.revision, CONTEXT, pids=pids, label="probe")
    )
    try:
        await asyncio.wait_for(started.wait(), 10)
        async with container.session_factory() as session:
            pids["revoke"] = await session.scalar(text("SELECT pg_backend_pid()"))
            await container.update_user(session).execute(authority, admin.id, None, False, CONTEXT)
        assert len(set(pids.values())) == 2
        release.set()
        with pytest.raises(Unauthenticated):
            await asyncio.wait_for(work, 10)
        async with container.session_factory() as session:
            assert (await SqlFirmsCredentials(session).get()).tested_at is None
    finally:
        await settle(release, work)


@pytest.mark.parametrize("change", ["clear", "rotate"])
@pytest.mark.parametrize("first", ["mutation", "publication"])
async def test_old_batch_release_and_key_change_have_one_guarded_order(
    client, container, admin, probe, monkeypatch, change, first
):
    actor, _ = await active(client, container, admin)
    state = await ready(container, actor)  # Tested replacement, old active key remains live.
    entered, release, waiting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    pids = {}
    scheduler = container.scheduler
    publish = scheduler._publish

    async def fetch(_connector):
        if first == "mutation":
            entered.set()
            await asyncio.wait_for(release.wait(), 10)
        return [make_event(source_id=SPEC.id)]

    async def held_publish(*args):
        # This callback is reached only while the real connector's DB release guard is held.
        assert pids["firms-poll"] is not None
        entered.set()
        await asyncio.wait_for(release.wait(), 10)
        return await publish(*args)

    monkeypatch.setattr(FirmsConnector, "fetch", fetch)
    if first == "publication":
        monkeypatch.setattr(scheduler, "_publish", held_publish)
        watch_lock(monkeypatch, "key-change", pids, waiting)
        watch_lock(monkeypatch, "firms-poll", pids, asyncio.Event())
    method, args = (
        ("confirm", (state.revision, state.test_generation, CONTEXT))
        if change == "rotate"
        else (
            "clear",
            (state.revision, CONTEXT),
        )
    )
    poll = asyncio.create_task(scheduler.poll_once(connector(container)), name="firms-poll")
    mutation = None
    try:
        await asyncio.wait_for(entered.wait(), 10)
        mutation = asyncio.create_task(invoke(container, actor, method, *args), name="key-change")
        if first == "publication":
            await asyncio.wait_for(waiting.wait(), 10)
            await observe_lock(container, pids["key-change"])
            assert len(set(pids.values())) == 2 and not mutation.done()
        else:
            await asyncio.wait_for(mutation, 10)
        release.set()
        result = await asyncio.wait_for(poll, 10)
        await asyncio.wait_for(mutation, 10)
        assert result.ok is (first == "publication")
        assert container.store.stats().total == int(first == "publication")
        assert container.health.get(SPEC.id).polls == int(first == "publication")
    finally:
        await settle(release, poll, mutation)
