"""Saved-report semantic search: isolation, bounded calls, version freshness and safe failures."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from ase.adapters.persistence.models import ReportRow
from ase.adapters.persistence.report_search import ReportEmbeddingRow, SqlReportEmbeddingRepository
from ase.container import Container
from ase.domain.errors import InvalidRequest, NoModelAvailable, RateLimited, Unauthenticated
from ase.domain.report_search import IndexedReport, profile_fingerprint
from ase.domain.users import User
from report_search_helpers import FakeEmbeddings, add_profile, add_report, service


async def test_unavailable_empty_and_object_policy(container: Container, user: User) -> None:
    gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        search = service(container, session, gateway)
        assert not (await search.status(user)).available
        with pytest.raises(NoModelAvailable, match="Admin, Models"):
            await search.index(user)
        with pytest.raises(NoModelAvailable):
            await search.query(user, "Shipping")
        await add_profile(container, session)
        assert (await search.status(user)).available
        assert (await search.index(user)).total == 0
        assert not (await search.query(user, "Shipping")).items
        assert not gateway.calls
        await container.repositories(session).users.save(replace(user, is_active=False))
        await session.commit()
        with pytest.raises(Unauthenticated):
            await search.status(user)


async def test_semantic_rank_cache_usage_and_changed_models(
    container: Container, user: User, admin: User
) -> None:
    gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        profile = await add_profile(container, session)
        shipping, _ = await add_report(container, session, user)
        space, _ = await add_report(container, session, user, "Space debris")
        search = service(container, session, gateway)
        assert (await search.index(user)).indexed == 2
        assert (await search.index(user)).indexed == 2
        assert len(gateway.calls) == 1
        # No words match the report title; ranking is the fake embedding's geometry.
        results = await search.query(user, "Merchant vessel chokepoints")
        assert [hit.report.id for hit in results.items] == [shipping.id, space.id]
        assert results.items[0].score == 1
        assert results.items[1].score == 0
        assert (await search.query(user, "Space traffic", 1)).items[0].report.id == space.id
        usages = await container.repositories(session).llm_usage.list_recent(20)
        assert len(usages) == 3
        assert all(u.user_id == user.id and u.purpose == "embeddings" and u.ok for u in usages)
        assert all(u.prompt_tokens == 30 for u in usages)
        fingerprint = profile_fingerprint(profile)
        profile.api_key_encrypted = container.cipher.encrypt("rotated-key")
        profile.temperature = 0.9
        assert profile_fingerprint(profile) == fingerprint
        profile.model = "new-model"
        await container.repositories(session).llm_profiles.save(profile)
        await session.commit()
        assert (await search.status(user)).indexed == 0
        assert not (await search.query(user, "Space")).items
        assert len(gateway.calls) == 3  # Search never silently regenerates the library.
        assert (await search.index(user)).indexed == 2
        assert len(gateway.calls) == 4


async def test_versions_deletions_and_mid_call_changes(container: Container, user: User) -> None:
    gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        profile = await add_profile(container, session)
        record, version = await add_report(container, session, user)
        search = service(container, session, gateway)
        await search.index(user)
        repos = container.repositories(session)
        record.latest_version = 2
        await repos.reports.add_version(record, replace(version, id=uuid4(), number=2))
        await session.commit()
        assert (await search.status(user)).indexed == 0
        assert not (await search.query(user, "Chokepoints")).items
        await search.index(user)
        assert (await search.query(user, "Chokepoints")).items[0].report.latest_version == 2

        async def remove_report() -> None:
            await repos.reports.delete(record.id)
            await session.commit()

        gateway.during_call = remove_report
        assert not (await search.query(user, "Chokepoints")).items
        assert (await search.status(user)).total == 0
        store = SqlReportEmbeddingRepository(session)
        assert not await store.save(
            IndexedReport(record.id, 2, profile_fingerprint(profile), (1.0,))
        )
        await search.index(user)
        assert not list(await session.scalars(select(ReportEmbeddingRow)))


async def test_batched_index_and_failures_are_safe(container: Container, user: User) -> None:
    gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        await add_profile(container, session)
        for index in range(10):
            await add_report(container, session, user, f"Maritime {index}")
        search = service(container, session, gateway)
        assert (await search.index(user)).indexed == 8
        assert len(gateway.calls[0]) == 8
        assert (await search.index(user)).indexed == 10
        assert len(gateway.calls[1]) == 2
        gateway.fail = True
        with pytest.raises(InvalidRequest, match="embeddings endpoint failed") as caught:
            await search.query(user, "private query")
        assert "DO NOT DISPLAY" not in str(caught.value)
        usage = await container.repositories(session).llm_usage.list_recent(20)
        failures = [call for call in usage if not call.ok]
        assert len(failures) == 1
        assert failures[0].user_id == user.id and failures[0].purpose == "embeddings"
        assert "DO NOT DISPLAY" not in str(failures[0].error)


async def test_limits_concurrency_dimensions_and_corrupt_cache(
    container: Container, user: User
) -> None:
    gateway = FakeEmbeddings()
    lock = asyncio.Lock()
    async with container.session_factory() as session:
        await add_profile(container, session)
        record, _ = await add_report(container, session, user)
        search = service(container, session, gateway, lock)
        for text, limit in ((" ", 10), ("q" * 501, 10), ("q", 21)):
            with pytest.raises(InvalidRequest):
                await search.query(user, text, limit)
        async with lock:
            with pytest.raises(RateLimited):
                await search.index(user)
            with pytest.raises(RateLimited):
                await search.query(user, "busy")
        await search.index(user)
        gateway.dimensions = 3
        with pytest.raises(InvalidRequest, match="dimensions changed"):
            await search.query(user, "query")
        row = await session.get(ReportEmbeddingRow, record.id)
        assert row is not None
        row.vector = [0.0, 0.0]
        await session.commit()
        assert (await search.status(user)).indexed == 0
        await search.index(user)
        for _ in range(30):
            container.limiter.hit(f"embedding:user:{user.id}", 30, 3600)
        with pytest.raises(RateLimited):
            await search.query(user, "budget")


async def test_new_versions_during_index_are_not_saved(container: Container, user: User) -> None:
    gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        await add_profile(container, session)
        record, version = await add_report(container, session, user)
        repos = container.repositories(session)

        async def supersede() -> None:
            record.latest_version = 2
            await repos.reports.add_version(record, replace(version, id=uuid4(), number=2))
            await session.commit()

        gateway.during_call = supersede
        search = service(container, session, gateway)
        assert (await search.index(user)).indexed == 0
        gateway.during_call = None
        assert (await search.index(user)).indexed == 1
        for _ in range(60):
            container.limiter.hit("embedding:global", 60, 3600)
        with pytest.raises(RateLimited):
            await search.query(user, "global call budget")


async def test_recent_library_has_a_hard_cap(container: Container, user: User) -> None:
    gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        await add_profile(container, session)
        oldest, _ = await add_report(container, session, user)
        for index in range(1000):
            session.add(
                ReportRow(
                    id=uuid4(),
                    template="intsum",
                    title=f"Saved {index}",
                    scope={},
                    period_from=oldest.period_from,
                    period_to=oldest.period_to,
                    data_cutoff=oldest.data_cutoff,
                    status="ready",
                    created_by=user.id,
                    created_at=oldest.created_at + timedelta(seconds=index + 1),
                    latest_version=1,
                )
            )
        await session.commit()
        status = await service(container, session, gateway).status(user)
        assert status.total == status.limit == 1000
        assert not gateway.calls
