"""Credential generations, source admission and idle behaviour at actual scheduler release."""

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.firms import SPEC, FirmsConnector
from ase.adapters.feeds.firms_runtime import ManagedFirmsConnector
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.persistence.firms_credentials import SqlFirmsCredentials
from ase.application.ports.feed_release import FeedUnavailable
from ase.domain.errors import Unauthenticated
from feeds_helpers import make_event
from team_helpers import CONTEXT
from test_firms_credentials import KEY, call, ready
from test_firms_credentials import probe as probe  # noqa: PLC0414
from test_saved_map_views import claims_for


def connector(container):
    return next(c for c in container.scheduler.connectors if c.spec.id == SPEC.id)


async def active(client, container, admin):
    actor = await claims_for(client, container, admin)
    state = await ready(container, actor)
    return actor, await call(
        container, actor, "confirm", state.revision, state.test_generation, CONTEXT
    )


async def test_unconfigured_source_registered_and_idle_without_upstream(container, monkeypatch):
    current = connector(container)
    assert isinstance(current, ManagedFirmsConnector)
    fetch = AsyncMock(side_effect=AssertionError("Must not contact NASA"))
    monkeypatch.setattr(FirmsConnector, "fetch", fetch)
    for _ in range(6):
        result = await container.scheduler.poll_once(current)
        assert not result.ok
    fetch.assert_not_called()
    assert container.health.get(SPEC.id).polls == 0


async def test_confirmed_key_is_used_on_next_poll_without_restart(
    client, container, admin, probe, monkeypatch
):
    current = connector(container)
    await active(client, container, admin)
    events = [make_event(source_id=SPEC.id)]
    monkeypatch.setattr(FirmsConnector, "fetch", AsyncMock(return_value=events))
    result = await container.scheduler.poll_once(current)
    assert result.ok and result.fetched == 1 and container.store.stats().total == 1
    assert current is connector(container)


@pytest.mark.parametrize("change", ["clear", "replace", "disable", "aba"])
async def test_inflight_batch_never_publishes_after_connection_or_activation_change(
    client, container, admin, probe, monkeypatch, change
):
    actor, state = await active(client, container, admin)

    async def fetch(_self):
        if change == "disable":
            async with container.session_factory() as session:
                await container.admin_source_controls(session).activate(
                    actor, SPEC.id, False, CONTEXT
                )
        else:
            await call(container, actor, "clear", state.revision, CONTEXT)
            if change in {"replace", "aba"}:
                next_state = await call(container, actor, "get")
                candidate = KEY if change == "aba" else KEY + "replaced"
                next_state = await call(
                    container, actor, "draft", candidate, next_state.revision, CONTEXT
                )
                tested = await call(container, actor, "test", next_state.revision, CONTEXT)
                await call(
                    container,
                    actor,
                    "confirm",
                    tested.status.revision,
                    tested.status.test_generation,
                    CONTEXT,
                )
        return [make_event(source_id=SPEC.id)]

    monkeypatch.setattr(FirmsConnector, "fetch", fetch)
    result = await container.scheduler.poll_once(connector(container))
    assert not result.ok and container.store.stats().total == 0
    assert container.health.get(SPEC.id).polls == 0


async def test_release_guard_rechecks_source_after_initial_admission(
    client, container, admin, probe
):
    actor, _ = await active(client, container, admin)
    async with container.session_factory() as session:
        await container.admin_source_controls(session).activate(actor, SPEC.id, False, CONTEXT)
    async with connector(container).release_guard(1) as allowed:
        assert not allowed


async def test_environment_precedence_and_disabled_veto(container, monkeypatch):
    fetch = AsyncMock(return_value=[])
    monkeypatch.setattr(FirmsConnector, "fetch", fetch)
    runtime = ManagedFirmsConnector(
        container.session_factory,
        container.http,
        container.clock,
        container.cipher,
        environment_key=KEY,
        area="world",
        disabled=False,
    )
    batch = await runtime.fetch_batch()
    assert batch.generation == -1
    async with runtime.release_guard(-1) as allowed:
        assert allowed
    runtime.disabled = True
    with pytest.raises(FeedUnavailable):
        await runtime.fetch_batch()
    assert fetch.await_count == 1


async def test_unreadable_key_and_upstream_exception_are_redacted(
    client, container, admin, probe, monkeypatch
):
    await active(client, container, admin)
    monkeypatch.setattr(FirmsConnector, "fetch", AsyncMock(side_effect=RuntimeError(KEY)))
    with pytest.raises(FeedFetchError) as failure:
        await connector(container).fetch_batch()
    assert KEY not in str(failure.value)
    async with container.session_factory() as session:
        repo = SqlFirmsCredentials(session)
        row = await repo.get()
        row.active_encrypted = "damaged-ciphertext"
        await repo.save(row)
        await session.commit()
    with pytest.raises(FeedFetchError, match="cannot be read"):
        await connector(container).fetch_batch()


@pytest.mark.parametrize("timeout", [False, True])
async def test_stale_failure_and_timeout_do_not_poison_new_connection(
    client, container, admin, probe, monkeypatch, timeout
):

    actor, state = await active(client, container, admin)

    async def fetch(_self):
        await call(container, actor, "clear", state.revision, CONTEXT)
        if timeout:
            await asyncio.sleep(10)
        raise RuntimeError(KEY)

    monkeypatch.setattr(FirmsConnector, "fetch", fetch)
    container.scheduler._fetch_timeout = timedelta(seconds=0.25)
    outcome = await container.scheduler.poll_once(connector(container))
    assert not outcome.ok and KEY not in repr(outcome)
    assert container.health.get(SPEC.id).polls == 0
    assert container.store.stats().total == 0


async def test_guard_verification_failure_is_opaque_and_next_poll_recovers(
    client, container, admin, probe, monkeypatch
):
    await active(client, container, admin)
    current = connector(container)
    original = current.release_guard

    @asynccontextmanager
    async def unavailable(generation):
        raise RuntimeError(KEY)
        yield False

    monkeypatch.setattr(current, "release_guard", unavailable)
    monkeypatch.setattr(FirmsConnector, "fetch", AsyncMock(side_effect=RuntimeError(KEY)))
    result = await container.scheduler.poll_once(current)
    assert not result.ok and KEY not in repr(result)
    assert container.health.get(SPEC.id).polls == 0
    monkeypatch.setattr(current, "release_guard", original)
    monkeypatch.setattr(FirmsConnector, "fetch", AsyncMock(return_value=[]))
    assert (await container.scheduler.poll_once(current)).ok


@pytest.mark.parametrize("change", ["clear", "replace"])
async def test_current_source_test_does_not_report_old_key_as_current_success(
    client, container, admin, probe, monkeypatch, change
):
    actor, state = await active(client, container, admin)

    async def fetch(_self):
        await call(container, actor, "clear", state.revision, CONTEXT)
        if change == "replace":
            candidate = await ready(container, actor)
            await call(
                container, actor, "confirm", candidate.revision, candidate.test_generation, CONTEXT
            )
        return [make_event(source_id=SPEC.id)]

    monkeypatch.setattr(FirmsConnector, "fetch", fetch)
    async with container.session_factory() as session:
        result = await container.admin_source_controls(session).test(actor, SPEC.id, CONTEXT)
    assert not result.ok and result.fetched == 0 and "changed" in result.message
    assert container.store.stats().total == 0 and container.health.get(SPEC.id).polls == 0


async def test_current_test_expiry_during_release_cleanup_denies_result(
    client, container, admin, probe, monkeypatch, clock
):
    actor, _ = await active(client, container, admin)
    current = connector(container)
    original = current.release_guard

    @asynccontextmanager
    async def expire_after_release(generation):
        async with original(generation) as allowed:
            yield allowed
        clock.advance(timedelta(minutes=16))

    monkeypatch.setattr(current, "release_guard", expire_after_release)
    monkeypatch.setattr(FirmsConnector, "fetch", AsyncMock(return_value=[]))
    async with container.session_factory() as session:
        with pytest.raises(Unauthenticated):
            await container.admin_source_controls(session).test(actor, SPEC.id, CONTEXT)
