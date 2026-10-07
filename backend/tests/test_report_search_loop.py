"""KAN-199: semantic search loads vectors once per query and keeps heavy work off the loop."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import Any
from uuid import UUID, uuid4

import pytest

from ase.adapters.persistence.report_search import (
    ReportEmbeddingRow,
    SqlReportEmbeddingRepository,
    _decoded,
)
from ase.container import Container
from ase.domain.report_search import IndexedReport, profile_fingerprint
from ase.domain.users import User
from report_search_helpers import FakeEmbeddings, add_profile, add_report, service


def record_calls(monkeypatch: pytest.MonkeyPatch) -> tuple[list[int], list[str]]:
    loads: list[int] = []
    threaded: list[str] = []
    original_current = SqlReportEmbeddingRepository.current
    original_thread = asyncio.to_thread

    async def current(
        self: SqlReportEmbeddingRepository, report_ids: Sequence[UUID], fingerprint: str
    ) -> list[IndexedReport]:
        loads.append(len(report_ids))
        return await original_current(self, report_ids, fingerprint)

    async def to_thread(function: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
        threaded.append(function.__name__)
        return await original_thread(function, *args, **kwargs)

    monkeypatch.setattr(SqlReportEmbeddingRepository, "current", current)
    monkeypatch.setattr(asyncio, "to_thread", to_thread)
    return loads, threaded


async def test_query_loads_vectors_once_and_scores_in_a_worker_thread(
    container: Container, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        await add_profile(container, session)
        shipping, _ = await add_report(container, session, user)
        space, _ = await add_report(container, session, user, "Space debris")
        search = service(container, session, gateway)
        assert (await search.index(user)).indexed == 2
        loads, threaded = record_calls(monkeypatch)
        result = await search.query(user, "Merchant vessel chokepoints")
    assert [hit.report.id for hit in result.items] == [shipping.id, space.id]
    assert result.indexed == 2
    assert loads == [2]
    assert threaded == ["_decoded", "ranked"]


async def test_an_empty_index_needs_no_vectors_and_no_model_call(
    container: Container, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        await add_profile(container, session)
        await add_report(container, session, user)
        search = service(container, session, gateway)
        loads, threaded = record_calls(monkeypatch)
        result = await search.query(user, "Shipping")
    assert result.items == () and result.total == 1
    assert loads == [] and threaded == [] and gateway.calls == []


async def test_existence_check_ignores_invalid_stale_and_foreign_entries(
    container: Container, user: User
) -> None:
    async with container.session_factory() as session:
        profile = await add_profile(container, session)
        fingerprint = profile_fingerprint(profile)
        record, _ = await add_report(container, session, user)
        repository = SqlReportEmbeddingRepository(session)
        assert not await repository.has_current([], fingerprint)
        assert not await repository.has_current([record.id], fingerprint)
        session.add(
            ReportEmbeddingRow(
                report_id=record.id, version=1, fingerprint=fingerprint, vector=[0.0, 0.0]
            )
        )
        await session.commit()
        assert not await repository.has_current([record.id], fingerprint)
        row = await session.get(ReportEmbeddingRow, record.id)
        assert row is not None
        row.vector = [1.0, 0.0]
        await session.commit()
        assert await repository.has_current([record.id], fingerprint)
        assert not await repository.has_current([record.id], "b" * 64)
        assert not await repository.has_current([uuid4()], fingerprint)
        row.version = 2
        await session.commit()
        assert not await repository.has_current([record.id], fingerprint)


def test_decoding_skips_corrupt_rows() -> None:
    valid = uuid4()
    rows = [
        (uuid4(), 1, "f", None),
        (uuid4(), 1, "f", "not json"),
        (uuid4(), 1, "f", "[0, 0]"),
        (uuid4(), 1, "f", '["a"]'),
        (valid, 1, "f", "[3, 4]"),
    ]
    assert _decoded(rows) == [IndexedReport(valid, 1, "f", (0.6, 0.8))]
