"""Async export admission and cancellation retain ownership of unfinished work."""

import asyncio
import threading

import pytest

from ase.adapters.reports.async_documents import AsyncReportDocumentRenderer
from ase.domain.errors import RateLimited
from ase.domain.report_documents import ExportFormat, ReportDocument

DOC = ReportDocument("title", "reference", ())


async def test_legacy_cancellation_keeps_two_slots_until_threads_finish():
    started = threading.Semaphore(0)
    release = threading.Event()

    class Legacy:
        def render(self, document, format):
            started.release()
            release.wait(5)
            return b"legacy"

    renderer = AsyncReportDocumentRenderer(legacy=Legacy())
    first = asyncio.create_task(renderer.render(DOC, ExportFormat.PDF))
    second = asyncio.create_task(renderer.render(DOC, ExportFormat.DOCX))
    assert await asyncio.to_thread(started.acquire, timeout=2)
    assert await asyncio.to_thread(started.acquire, timeout=2)
    try:
        first.cancel()
        await asyncio.sleep(0)
        assert not first.done()
        with pytest.raises(RateLimited):
            await renderer.render(DOC, ExportFormat.PDF)
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert await second == b"legacy"
    assert await renderer.render(DOC, ExportFormat.PDF) == b"legacy"


async def test_configured_worker_routes_only_arabic_persian_pdf_and_propagates_cancel():
    entered, stopped = asyncio.Event(), asyncio.Event()

    class Worker:
        async def render(self, document):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

    class Legacy:
        def render(self, document, format):
            return b"legacy"

    renderer = AsyncReportDocumentRenderer(worker=Worker(), legacy=Legacy())
    assert await renderer.render(DOC, ExportFormat.PDF) == b"legacy"
    assert (
        await renderer.render(ReportDocument("title", "reference", (), "ar"), ExportFormat.DOCX)
        == b"legacy"
    )
    task = asyncio.create_task(
        renderer.render(ReportDocument("title", "reference", (), "fa"), ExportFormat.PDF)
    )
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stopped.is_set()
