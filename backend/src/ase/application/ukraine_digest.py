"""Cadence, caching and honest states for the fortnightly Ukraine digest.

One digest a fortnight is written from sources already collected, plus an administrator
forced refresh. Readers never start work beyond that rule, and a failed attempt waits
before it is tried again. Prompts are never stored.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from ase.application.policy import require_admin
from ase.application.ports import Clock, RateLimiter
from ase.application.ports.llm import LlmGatewayError
from ase.application.ports.source_controls import SourceAdmission
from ase.application.ports.ukraine_digest import UkraineDigestStore
from ase.application.ukraine import UkraineBoard
from ase.application.ukraine_digest_evidence import evidence_pack
from ase.application.ukraine_digest_writer import DigestRejected, DigestWriter
from ase.domain.errors import RateLimited
from ase.domain.llm import LlmProfile
from ase.domain.ukraine.digest import DIGEST_INTERVAL, DIGEST_RETENTION, StoredDigest
from ase.domain.users import User

log = logging.getLogger(__name__)
# A failed attempt is not repeated on the next page view.
RETRY_AFTER = timedelta(hours=6)
REFRESH_PER_DAY = 4
REFRESH_PER_ADMIN_HOUR = 2
NO_MODEL = "No model is assigned, so no digest can be written."
NO_EVIDENCE = "No Ukraine reporting was retained for this fortnight, so there is nothing to read."


class DigestStatus(StrEnum):
    READY = "ready"
    NONE = "none"
    GENERATING = "generating"
    UNAVAILABLE = "unavailable"
    VALIDATION_FAILED = "validation_failed"


@dataclass(frozen=True, slots=True)
class DigestView:
    status: DigestStatus
    reason: str | None
    stale: bool
    generating: bool
    interval_days: int
    latest: StoredDigest | None
    previous: tuple[StoredDigest, ...]


class DigestModelRuntime(Protocol):
    async def profile(self) -> LlmProfile | None:
        """The assigned assessment profile, or None when no usable model is configured."""
        ...


AuditRecorder = Callable[[UUID, str | None], Awaitable[None]]


class UkraineDigestService:
    def __init__(
        self,
        board: Callable[[], UkraineBoard],
        store: UkraineDigestStore,
        runtime: DigestModelRuntime,
        writer: DigestWriter,
        clock: Clock,
        admission: SourceAdmission,
        limiter: RateLimiter,
        audit: AuditRecorder,
    ) -> None:
        self._board, self._store, self._runtime = board, store, runtime
        self._writer, self._clock = writer, clock
        self._admission, self._limiter, self._audit = admission, limiter, audit
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._failure: tuple[DigestStatus, str] | None = None
        self._next_attempt: datetime | None = None

    async def view(self) -> DigestView:
        """What a reader sees. Starts one generation when the fortnight is up."""
        stored = await self._store.recent(DIGEST_RETENTION)
        latest = stored[0] if stored else None
        now = self._clock.now()
        due = latest is None or latest.is_due(now)
        if due and (self._next_attempt is None or now >= self._next_attempt):
            self._schedule()
        return self._compose(stored, due)

    async def refresh(self, actor: User, ip: str | None) -> DigestView:
        """An administrator asks for a new digest now; audited and rate limited."""
        require_admin(actor)
        for key, limit, window in (
            (f"ukraine-digest-refresh:{actor.id}", REFRESH_PER_ADMIN_HOUR, 3_600),
            ("ukraine-digest-refresh", REFRESH_PER_DAY, 86_400),
        ):
            retry = self._limiter.hit(key, limit, window)
            if retry is not None:
                raise RateLimited(retry)
        await self._audit(actor.id, ip)
        self._next_attempt = None
        self._schedule()
        stored = await self._store.recent(DIGEST_RETENTION)
        return self._compose(stored, True)

    async def drain(self) -> None:
        """Wait for any generation in flight; used by tests and on shutdown."""
        task = self._task
        if task is not None:
            with suppress(asyncio.CancelledError):
                await task

    def cancel(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()

    def _compose(self, stored: list[StoredDigest], due: bool) -> DigestView:
        generating = self._task is not None and not self._task.done()
        latest = stored[0] if stored else None
        # A stored digest is always returned; the status says what the last attempt did.
        status, reason = DigestStatus.NONE, None
        if latest is not None:
            status = DigestStatus.READY
        if generating:
            status = DigestStatus.GENERATING
        if self._failure is not None:
            status, reason = self._failure
        return DigestView(
            status=status,
            reason=reason,
            stale=due and latest is not None,
            generating=generating,
            interval_days=DIGEST_INTERVAL.days,
            latest=latest,
            previous=tuple(stored[1:]),
        )

    def _schedule(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        try:
            await self.generate()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.warning("ukraine_digest.generation_failed", exc_info=True)
            self._fail(DigestStatus.UNAVAILABLE, "The digest could not be written.")

    async def generate(self) -> None:
        """Write one digest now. Concurrent callers wait rather than paying twice."""
        async with self._lock:
            await self._generate()

    async def _generate(self) -> None:
        profile = await self._runtime.profile()
        if profile is None:
            self._fail(DigestStatus.UNAVAILABLE, NO_MODEL)
            return
        pack = evidence_pack(self._board(), self._clock.now())
        if not pack.items:
            self._fail(DigestStatus.UNAVAILABLE, NO_EVIDENCE)
            return
        try:
            # No guard and no transaction is held across the provider call.
            written = await self._writer.write(profile, pack)
        except DigestRejected as rejected:
            self._fail(
                DigestStatus.VALIDATION_FAILED,
                "The model answer did not pass the checks this application runs before "
                "storing a digest, so nothing was saved.",
            )
            log.warning("ukraine_digest.rejected", extra={"checks": len(rejected.errors)})
            return
        except LlmGatewayError as error:
            self._fail(DigestStatus.UNAVAILABLE, str(error))
            return
        stored = StoredDigest(
            period_start=pack.period_start,
            period_end=pack.period_end,
            generated_at=self._clock.now(),
            model=written.model,
            digest=written.digest,
            citations=written.citations,
            source_ids=pack.source_ids,
            evidence_items=len(pack.items),
            prompt_tokens=written.prompt_tokens,
            completion_tokens=written.completion_tokens,
        )
        # Same guard order as source administration, taken only for the final write.
        async with self._admission.guard():
            await self._store.save(stored, DIGEST_RETENTION)
        self._failure, self._next_attempt = None, None

    def _fail(self, status: DigestStatus, reason: str) -> None:
        self._failure = (status, reason)
        self._next_attempt = self._clock.now() + RETRY_AFTER
