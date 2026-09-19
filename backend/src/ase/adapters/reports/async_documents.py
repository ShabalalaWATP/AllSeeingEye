"""Awaitable export admission, retaining capacity until all work has stopped."""

import asyncio
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Protocol

from ase.adapters.reports.documents import ReportDocumentRenderer
from ase.application.ports.report_export import RenderCleanupFailed, ReportRenderer
from ase.domain.errors import RateLimited
from ase.domain.report_documents import ExportFormat, ReportDocument

_SLOTS = threading.BoundedSemaphore(2)
_RETIRED: set[asyncio.Task[None]] = set()


@dataclass(slots=True)
class _Lease:
    actor: str
    retained: int = 0
    closed: bool = False


@dataclass(slots=True)
class _RequestState:
    total: int = 0
    by_actor: dict[str, int] = field(default_factory=dict)


_REQUESTS = _RequestState()


_LEASE: ContextVar[_Lease | None] = ContextVar("report_document_lease", default=None)


class PdfWorker(Protocol):
    async def render(self, document: ReportDocument) -> bytes: ...


def _release_request(lease: _Lease) -> None:
    _REQUESTS.total -= 1
    remaining = _REQUESTS.by_actor[lease.actor] - 1
    if remaining:
        _REQUESTS.by_actor[lease.actor] = remaining
    else:
        _REQUESTS.by_actor.pop(lease.actor, None)


@asynccontextmanager
async def document_request(actor: str, *, deadline_seconds: float = 120.0) -> AsyncIterator[None]:
    """Bound one caller's public document work and retain ownership after timeout."""
    if _REQUESTS.total >= 2 or _REQUESTS.by_actor.get(actor, 0) >= 1:
        raise RateLimited(5)
    _REQUESTS.total += 1
    _REQUESTS.by_actor[actor] = _REQUESTS.by_actor.get(actor, 0) + 1
    lease = _Lease(actor)
    token = _LEASE.set(lease)
    try:
        async with asyncio.timeout(deadline_seconds):
            yield
    finally:
        _LEASE.reset(token)
        lease.closed = True
        if lease.retained == 0:
            _release_request(lease)


async def _retire[T](task: asyncio.Task[T], lease: _Lease | None) -> None:
    release_slot = True
    try:
        await task
    except RenderCleanupFailed:
        release_slot = False
    except Exception:
        release_slot = True
    finally:
        if release_slot:
            _SLOTS.release()
        if lease is not None:
            lease.retained -= 1
            if lease.closed and lease.retained == 0:
                _release_request(lease)


def _retire_later[T](task: asyncio.Task[T], lease: _Lease | None) -> None:
    if lease is not None:
        lease.retained += 1
    retired = asyncio.create_task(_retire(task, lease))
    _RETIRED.add(retired)
    retired.add_done_callback(_RETIRED.discard)


async def run_bounded_thread[T](operation: Callable[[], T], *, wait_for_slot: bool = False) -> T:
    """Run CPU-heavy document work off-loop within shared export admission."""
    if wait_for_slot:
        async with asyncio.timeout(5):
            while not _SLOTS.acquire(blocking=False):
                await asyncio.sleep(0.05)
    elif not _SLOTS.acquire(blocking=False):
        raise RateLimited(5)
    task = asyncio.create_task(asyncio.to_thread(operation))
    release = True
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        _retire_later(task, _LEASE.get())
        release = False
        raise
    except RenderCleanupFailed:
        release = False
        raise
    finally:
        if release:
            _SLOTS.release()


class AsyncReportDocumentRenderer:
    def __init__(
        self, *, worker: PdfWorker | None = None, legacy: ReportRenderer | None = None
    ) -> None:
        self.worker = worker
        self.legacy = legacy or ReportDocumentRenderer()

    async def render(self, document: ReportDocument, format: ExportFormat) -> bytes:
        if not _SLOTS.acquire(blocking=False):
            raise RateLimited(5)
        release = True
        try:
            if (
                self.worker is not None
                and format is ExportFormat.PDF
                and document.language in {"ar", "fa"}
            ):
                # The worker owns cancellation, deadline and descendant cleanup.
                return await self.worker.render(document)
            task = asyncio.create_task(asyncio.to_thread(self.legacy.render, document, format))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                _retire_later(task, _LEASE.get())
                release = False
                raise
        except RenderCleanupFailed:
            release = False
            raise
        finally:
            if release:
                _SLOTS.release()
