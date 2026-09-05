"""Explicit, bounded embedding of saved reports and similarity search of current versions."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence

from ase.application.ports.embeddings import EmbeddingGateway, ReportEmbeddingRepository
from ase.application.ports.llm import LlmProfileRepository, LlmUsageRepository, SecretCipher
from ase.application.ports.reports import ReportRepository
from ase.application.ports.repositories import UnitOfWork
from ase.application.ports.services import Clock, RateLimiter
from ase.application.reports.access import GetReportUseCase
from ase.domain.errors import Forbidden, InvalidRequest, NoModelAvailable, NotFound, RateLimited
from ase.domain.llm import LlmProfile, LlmRole, LlmUsage
from ase.domain.report_records import ReportRecord
from ase.domain.report_search import (
    INDEX_BATCH,
    MAX_REPORTS,
    EmbeddingResult,
    IndexedReport,
    SearchHit,
    SearchResult,
    SearchStatus,
    checked_vector,
    cosine,
    profile_fingerprint,
    report_text,
)
from ase.domain.users import User

UNAVAILABLE = "Semantic search needs an enabled embeddings profile under Admin, Models."
EMBEDDING_FAILED = "The embeddings endpoint failed. Check the embeddings profile in Admin, Models."


class ReportSearchService:
    def __init__(
        self,
        *,
        reports: ReportRepository,
        embeddings: ReportEmbeddingRepository,
        profiles: LlmProfileRepository,
        usage: LlmUsageRepository,
        cipher: SecretCipher,
        gateway: EmbeddingGateway,
        clock: Clock,
        limiter: RateLimiter,
        lock: asyncio.Lock,
        uow: UnitOfWork,
    ) -> None:
        self._reports = reports
        self._embeddings = embeddings
        self._profiles = profiles
        self._usage = usage
        self._cipher = cipher
        self._gateway = gateway
        self._clock = clock
        self._limiter = limiter
        self._lock = lock
        self._uow = uow

    async def _profile(self) -> LlmProfile | None:
        profiles = await self._profiles.list_all()
        return next(
            (
                profile
                for profile in profiles
                if profile.allows(LlmRole.EMBEDDINGS) and self._cipher.available
            ),
            None,
        )

    async def _records(self, actor: User) -> list[ReportRecord]:
        if not actor.is_active:
            raise Forbidden()
        # Matches the saved report library: every active signed-in user can read reports.
        return await self._reports.list_recent(MAX_REPORTS)

    async def status(self, actor: User) -> SearchStatus:
        records = await self._records(actor)
        profile = await self._profile()
        entries = (
            await self._embeddings.current(
                [record.id for record in records], profile_fingerprint(profile)
            )
            if profile
            else []
        )
        return SearchStatus(profile is not None, len(entries), len(records))

    def _budget(self, actor: User) -> None:
        for key, limit in ((f"embedding:user:{actor.id}", 30), ("embedding:global", 60)):
            retry = self._limiter.hit(key, limit, 3600)
            if retry is not None:
                raise RateLimited(retry)

    async def _embed(
        self, actor: User, profile: LlmProfile, texts: Sequence[str]
    ) -> EmbeddingResult:
        self._budget(actor)
        started = time.perf_counter()
        try:
            key = self._cipher.decrypt(profile.api_key_encrypted)
            async with asyncio.timeout(35):
                result = await self._gateway.embed(profile.base_url, key, profile.model, texts)
            vectors = tuple(checked_vector(vector) for vector in result.vectors)
            if len(vectors) != len(texts) or len({len(vector) for vector in vectors}) != 1:
                raise ValueError("Invalid vectors.")
        except Exception as exc:
            await self._usage.add(
                LlmUsage(
                    at=self._clock.now(),
                    profile_id=profile.id,
                    user_id=actor.id,
                    purpose="embeddings",
                    ok=False,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    error=EMBEDDING_FAILED,
                )
            )
            await self._uow.commit()
            raise InvalidRequest(EMBEDDING_FAILED) from exc
        await self._usage.add(
            LlmUsage(
                at=self._clock.now(),
                profile_id=profile.id,
                user_id=actor.id,
                purpose="embeddings",
                ok=True,
                latency_ms=result.latency_ms,
                prompt_tokens=result.prompt_tokens,
            )
        )
        return EmbeddingResult(vectors, result.latency_ms, result.prompt_tokens)

    async def index(self, actor: User) -> SearchStatus:
        # One shared lock spans the cache check and write, preventing duplicate paid calls.
        if self._lock.locked():
            raise RateLimited(1)
        async with self._lock:
            records = await self._records(actor)
            profile = await self._profile()
            if profile is None:
                raise NoModelAvailable(UNAVAILABLE)
            fingerprint = profile_fingerprint(profile)
            existing = await self._embeddings.current([r.id for r in records], fingerprint)
            current_ids = {entry.report_id for entry in existing}
            selected = []
            texts = []
            for record in records:
                if record.id in current_ids:
                    continue
                try:
                    current, version = await GetReportUseCase(self._reports).execute(
                        actor, record.id
                    )
                except NotFound:
                    continue
                selected.append((current.id, version.number))
                texts.append(report_text(current, version))
                if len(selected) == INDEX_BATCH:
                    break
            if selected:
                result = await self._embed(actor, profile, texts)
                for (report_id, number), vector in zip(selected, result.vectors, strict=True):
                    await self._embeddings.save(
                        IndexedReport(report_id, number, fingerprint, vector)
                    )
            # Retain only current library ids, even when a report vanished during the call.
            await self._embeddings.retain([r.id for r in await self._records(actor)])
            await self._uow.commit()
            return await self.status(actor)

    async def query(self, actor: User, query: str, limit: int = 10) -> SearchResult:
        text = query.strip()
        if not 1 <= len(text) <= 500 or not 1 <= limit <= 20:
            raise InvalidRequest("Enter a search of 1 to 500 characters and at most 20 results.")
        if self._lock.locked():
            raise RateLimited(1)
        async with self._lock:
            records = await self._records(actor)
            profile = await self._profile()
            if profile is None:
                raise NoModelAvailable(UNAVAILABLE)
            fingerprint = profile_fingerprint(profile)
            entries = await self._embeddings.current([r.id for r in records], fingerprint)
            if not entries:
                return SearchResult((), 0, len(records))
            result = await self._embed(actor, profile, [text])
            await self._uow.commit()
            # Re-read after the outbound call: deleted or superseded reports cannot leak.
            records = await self._records(actor)
            entries = await self._embeddings.current([r.id for r in records], fingerprint)
            query_vector = result.vectors[0]
            if any(len(entry.vector) != len(query_vector) for entry in entries):
                raise InvalidRequest(
                    "The model's embedding dimensions changed. Configure a new embeddings "
                    "profile and index the saved reports again."
                )
            by_id = {record.id: record for record in records}
            hits = sorted(
                (
                    SearchHit(by_id[entry.report_id], cosine(query_vector, entry.vector))
                    for entry in entries
                ),
                key=lambda hit: (-hit.score, str(hit.report.id)),
            )
            return SearchResult(tuple(hits[:limit]), len(entries), len(records))
