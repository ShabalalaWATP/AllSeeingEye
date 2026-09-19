"""Async export admission and cancellation retain ownership of unfinished work."""

import asyncio
import threading

import pytest

from ase.adapters.reports import async_documents
from ase.adapters.reports.async_documents import AsyncReportDocumentRenderer, run_bounded_thread
from ase.domain.errors import RateLimited
from ase.domain.report_documents import ExportFormat, ReportDocument

DOC = ReportDocument("title", "reference", ())


async def test_legacy_cancellation_returns_promptly_but_keeps_slots_until_threads_finish():
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
        assert first.done()
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


async def test_generic_document_work_returns_promptly_and_retires_its_slot():
    started = threading.Event()
    release = threading.Event()

    def render_package():
        started.set()
        release.wait(5)
        return "package"

    task = asyncio.create_task(run_bounded_thread(render_package))
    assert await asyncio.to_thread(started.wait, 2)
    task.cancel()
    await asyncio.sleep(0)
    assert task.done()
    with pytest.raises(asyncio.CancelledError):
        await task
    release.set()
    await asyncio.sleep(0.05)
    assert await run_bounded_thread(lambda: "next") == "next"


async def test_internal_document_work_waits_for_shared_capacity(monkeypatch):
    slots = threading.BoundedSemaphore(2)
    monkeypatch.setattr(async_documents, "_SLOTS", slots)
    assert slots.acquire(blocking=False)
    assert slots.acquire(blocking=False)

    waiting = asyncio.create_task(run_bounded_thread(lambda: "finished", wait_for_slot=True))
    await asyncio.sleep(0.1)
    assert not waiting.done()
    slots.release()
    assert await asyncio.wait_for(waiting, 2) == "finished"
    slots.release()
