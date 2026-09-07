"""Opt-in PostgreSQL writer races against separately generated disposable databases."""

import asyncio
import os
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from ase.adapters.persistence.models import AuditLogRow
from ase.adapters.persistence.relationship_models import (
    RelationshipReviewRow,
    RelationshipRevisionRow,
)
from ase.adapters.persistence.users import SqlUserRepository
from ase.application.reports import relationships
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from team_helpers import CONTEXT, team_service
from test_report_relationship_service import VALUE, create, seed_report
from test_report_relationship_teams import team_report
from test_report_team_scope import team_for
from test_saved_map_views import claims_for


@pytest.fixture
async def settings(settings):
    source = os.environ.get("ASE_RELATIONSHIP_CONCURRENCY_POSTGRES_URL")
    if not source:
        pytest.skip(
            "Set ASE_RELATIONSHIP_CONCURRENCY_POSTGRES_URL to an owned disposable PG server"
        )
    url = make_url(source)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    name = f"ase_relationship_race_{uuid4().hex}"
    engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{name}"'))
        try:
            # conftest creates/drops schema only inside this newly generated database.
            yield settings.model_copy(
                update={
                    "database_url": url.set(database=name).render_as_string(hide_password=False)
                }
            )
        finally:
            async with engine.connect() as connection:
                await connection.execute(text(f'DROP DATABASE "{name}"'))
    finally:
        await engine.dispose()


async def wait_for_database_lock(container, pid):
    async with asyncio.timeout(5), container.session_factory() as session:
        while True:
            wait = await session.scalar(
                text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"),
                {"pid": pid},
            )
            if wait == "Lock":
                return
            await session.rollback()
            await asyncio.sleep(0.01)


def simultaneous_lock(monkeypatch, container):
    original = SqlUserRepository.lock_administration
    held, waiting, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    pids = []

    async def lock(repository):
        index = len(pids)
        pids.append(None)
        pids[index] = await repository._session.scalar(text("SELECT pg_backend_pid()"))
        if index == 0:
            await original(repository)
            held.set()
            await asyncio.wait_for(release.wait(), 10)
        else:
            await asyncio.wait_for(held.wait(), 10)
            waiting.set()
            await original(repository)

    async def observe():
        try:
            await asyncio.wait_for(waiting.wait(), 10)
            await wait_for_database_lock(container, pids[1])
        finally:
            release.set()

    monkeypatch.setattr(SqlUserRepository, "lock_administration", lock)
    return pids, asyncio.create_task(observe())


async def retained(container):
    async with container.session_factory() as session:
        roots = list(await session.scalars(select(RelationshipReviewRow)))
        revisions = list(await session.scalars(select(RelationshipRevisionRow)))
        audited = await session.scalar(
            select(func.count())
            .select_from(AuditLogRow)
            .where(AuditLogRow.action.in_(["relationship.created", "relationship.revised"]))
        )
        return roots, revisions, audited


@pytest.mark.parametrize("team_scope", [False, True], ids=["personal", "team"])
@pytest.mark.parametrize("quota", ["count", "bytes"])
async def test_last_relationship_quota_slot_serialises_independent_writers(
    client, container, admin, user, monkeypatch, team_scope, quota
):
    team = await team_for(container, admin, user) if team_scope else None
    user_claims = await claims_for(client, container, user)
    admin_claims = await claims_for(client, container, admin)
    owners = [user, user, admin if team else user]
    reports = [
        (
            await team_report(container, owner, team)
            if team
            else await seed_report(container, owner)
        )[0]
        for owner in owners
    ]
    initial = await create(container, user_claims, reports[0])
    async with container.session_factory() as session:
        repository = container.report_relationships(session).relationships
        initial_count, initial_bytes = await repository.scope_usage(
            user.id, team.id if team else None
        )
    assert initial_count == 1
    if quota == "count":
        monkeypatch.setattr(relationships, "MAX_SCOPE_DECISIONS", 2)
    else:
        # Same frozen assertion/rationale and fixed-width IDs give equal charged sizes.
        # The allowance comes from actual persisted usage, not a stubbed quota repository.
        monkeypatch.setattr(relationships, "MAX_SCOPE_BYTES", 2 * initial_bytes)
    pids, observer = simultaneous_lock(monkeypatch, container)
    async with asyncio.timeout(20):
        outcomes = await asyncio.gather(
            create(container, user_claims, reports[1]),
            create(container, admin_claims if team else user_claims, reports[2]),
            return_exceptions=True,
        )
    await observer
    assert len(set(pids)) == 2, "Race must use two separate PostgreSQL server connections"
    assert sum(isinstance(item, InvalidRequest) for item in outcomes) == 1, outcomes
    winner = next(item for item in outcomes if not isinstance(item, BaseException))
    roots, revisions, audited = await retained(container)
    assert len(roots) == len(revisions) == audited == 2
    assert {item.id for item in revisions} == {initial.id, winner.id}
    assert sum(item.byte_size for item in revisions) <= 2 * initial_bytes
    async with container.session_factory() as session:
        service = container.report_relationships(session)
        assert (await service.get(user_claims, initial.relationship_id, initial.id))[1] == initial


async def test_same_base_service_corrections_keep_one_winner_and_immutable_history(
    client, container, user, monkeypatch
):
    claims = await claims_for(client, container, user)
    record, _ = await seed_report(container, user)
    first = await create(container, claims, record)
    pids, observer = simultaneous_lock(monkeypatch, container)

    async def correct(rationale):
        async with container.session_factory() as session:
            return await container.report_relationships(session).update(
                claims,
                first.relationship_id,
                first.id,
                replace(VALUE, rationale=rationale),
                CONTEXT,
            )

    async with asyncio.timeout(20):
        outcomes = await asyncio.gather(
            correct("Correction A"), correct("Correction B"), return_exceptions=True
        )
    await observer
    assert len(set(pids)) == 2
    assert sum(isinstance(item, Conflict) for item in outcomes) == 1, outcomes
    winner = next(item for item in outcomes if not isinstance(item, BaseException))
    roots, revisions, audited = await retained(container)
    assert len(roots) == 1 and len(revisions) == audited == 2
    assert roots[0].latest_revision_id == winner.id
    assert winner.number == 2 and winner.previous_id == first.id
    async with container.session_factory() as session:
        service = container.report_relationships(session)
        assert (await service.get(claims, first.relationship_id, first.id))[1] == first
        assert (await service.get(claims, first.relationship_id))[1] == winner


async def test_repository_compare_and_swap_is_atomic_without_application_guard(
    client, container, user
):
    claims = await claims_for(client, container, user)
    record, _ = await seed_report(container, user)
    first = await create(container, claims, record)
    ready = asyncio.Event()
    pids = []
    proposals = [
        replace(
            first,
            id=uuid4(),
            number=2,
            previous_id=first.id,
            rationale=f"Independent repository correction {index}",
        )
        for index in range(2)
    ]

    async def append(proposal):
        async with container.session_factory() as session:
            repository = container.report_relationships(session).relationships
            assert (await repository.get(first.relationship_id)).latest_revision_id == first.id
            pids.append(await session.scalar(text("SELECT pg_backend_pid()")))
            if len(pids) == 2:
                ready.set()
            await asyncio.wait_for(ready.wait(), 10)
            won = await repository.append(proposal, first.id)
            await session.commit()
            return won

    async with asyncio.timeout(20):
        outcomes = await asyncio.gather(*(append(item) for item in proposals))
    assert len(set(pids)) == 2 and sorted(outcomes) == [False, True]
    roots, revisions, audited = await retained(container)
    winner = proposals[outcomes.index(True)]
    assert len(roots) == 1 and len(revisions) == 2 and audited == 1
    assert roots[0].latest_revision_id == winner.id
    assert {item.id for item in revisions} == {first.id, winner.id}


async def test_membership_revocation_while_writer_waits_denies_correction(
    client, container, admin, user, monkeypatch
):
    team = await team_for(container, admin, user)
    claims = await claims_for(client, container, user)
    record, _ = await team_report(container, user, team)
    first = await create(container, claims, record)
    locked, waiting, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    pids = {}
    original = SqlUserRepository.lock_administration

    async def lock(repository):
        task = asyncio.current_task()
        name = task.get_name() if task else ""
        if name in {"relationship-revoker", "relationship-writer"}:
            pids[name] = await repository._session.scalar(text("SELECT pg_backend_pid()"))
        if name == "relationship-writer":
            waiting.set()
        await original(repository)
        if name == "relationship-revoker":
            locked.set()
            await asyncio.wait_for(release.wait(), 10)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", lock)

    async def revoke():
        async with team_service(container) as service:
            await service.remove_member(admin, team.id, user.id, CONTEXT)

    async def correct():
        async with container.session_factory() as session:
            return await container.report_relationships(session).update(
                claims, first.relationship_id, first.id, VALUE, CONTEXT
            )

    revoker = asyncio.create_task(revoke(), name="relationship-revoker")
    writer = None
    try:
        await asyncio.wait_for(locked.wait(), 10)
        writer = asyncio.create_task(correct(), name="relationship-writer")
        await asyncio.wait_for(waiting.wait(), 10)
        await wait_for_database_lock(container, pids["relationship-writer"])
        assert len(set(pids.values())) == 2
        release.set()
        await revoker
        with pytest.raises(NotFound):
            await writer
    finally:
        release.set()
        for task in (revoker, writer):
            if task is not None and not task.done():
                task.cancel()
        await asyncio.gather(*(task for task in (revoker, writer) if task), return_exceptions=True)
    roots, revisions, audited = await retained(container)
    assert len(roots) == len(revisions) == audited == 1
    assert roots[0].latest_revision_id == first.id
