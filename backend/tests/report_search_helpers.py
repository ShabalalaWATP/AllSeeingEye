"""Offline embedding fixtures with distinct semantic directions for saved report topics."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_search import SqlReportEmbeddingRepository
from ase.application.ports.embeddings import EmbeddingGatewayError
from ase.application.reports.search import ReportSearchService
from ase.container import Container
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.report_search import EmbeddingResult
from ase.domain.users import User
from report_documents_helpers import document_records


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.fail = False
        self.dimensions = 2
        self.during_call: Callable[[], Awaitable[None]] | None = None

    async def aclose(self) -> None:
        pass

    async def embed(
        self, base_url: str, api_key: str, model: str, texts: Sequence[str]
    ) -> EmbeddingResult:
        self.calls.append(tuple(texts))
        if self.during_call:
            await self.during_call()
        if self.fail:
            raise EmbeddingGatewayError("DO NOT DISPLAY provider key or report body")
        vectors = tuple(
            ((0.0, 1.0) if text.startswith("Space") else (1.0, 0.0))
            + ((0.0,) if self.dimensions == 3 else ())
            for text in texts
        )
        return EmbeddingResult(vectors, latency_ms=4.0, prompt_tokens=30)


async def add_profile(container: Container, session: AsyncSession) -> LlmProfile:
    profile = LlmProfile(
        id=uuid4(),
        name="Offline semantic model",
        base_url="http://localhost:11434/v1",
        model="test-embeddings",
        api_key_encrypted=container.cipher.encrypt("test-key"),
        api_key_hint="-key",
        roles=frozenset({LlmRole.EMBEDDINGS}),
        max_output_tokens=64,
        temperature=0.0,
        enabled=True,
        created_at=container.clock.now(),
        updated_at=container.clock.now(),
    )
    await container.repositories(session).llm_profiles.add(profile)
    await session.commit()
    return profile


async def add_report(
    container: Container, session: AsyncSession, actor: User, title: str = "Maritime warning"
) -> tuple[ReportRecord, ReportVersion]:
    record, version = document_records(actor.id)
    record.title = title
    await container.repositories(session).reports.add(record, version)
    await session.commit()
    return record, version


def service(
    container: Container,
    session: AsyncSession,
    gateway: FakeEmbeddings,
    lock: asyncio.Lock | None = None,
) -> ReportSearchService:
    repos = container.repositories(session)
    return ReportSearchService(
        reports=repos.reports,
        embeddings=SqlReportEmbeddingRepository(session),
        profiles=repos.llm_profiles,
        usage=repos.llm_usage,
        cipher=container.cipher,
        gateway=gateway,
        clock=container.clock,
        limiter=container.limiter,
        lock=lock or asyncio.Lock(),
        uow=repos.uow,
    )
