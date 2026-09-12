"""Owned subprocess fixtures exercise transport, deadlines and complete cleanup."""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from ase.adapters.reports import async_documents, chromium, chromium_runtime
from ase.adapters.reports.chromium import ChromiumPdfWorker
from ase.adapters.reports.chromium_runtime import LinuxChromiumPolicy
from ase.application.ports.report_export import RenderCleanupFailed
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import ExportFormat, ReportDocument

DOC = ReportDocument("Private fixture", "reference", (), "ar")


class Job:
    def __init__(self, directory):
        self.path = self.root = directory
        self.processes = []
        self.closed = False
        self.fail = False

    async def close(self):
        for process in self.processes:
            if process.returncode is None:
                process.kill()
            await process.wait()
        self.closed = True
        if self.fail:
            raise OSError("private runtime path")


class Policy:
    def __init__(self):
        self.jobs = []

    def prepare(self, directory):
        job = Job(directory)
        self.jobs.append(job)
        return job

    def command(self, directory):
        return ["controlled-owned-fixture"]


@pytest.fixture
def runtime(monkeypatch):
    policy = Policy()

    async def spawn(directory):
        script = (
            "import sys,json; "
            "sys.stdout.buffer.write(json.dumps({'pages':1,'bytes':16}).encode()"
            "+b'\\n%PDF-1.7 fixture')"
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-c",
            script,
            cwd=directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        policy.jobs[-1].processes.append(process)
        return process

    monkeypatch.setattr(chromium, "_spawn", spawn)
    return policy


async def test_bounded_owned_worker_completes_and_reaps(runtime):
    # The transport fixture is not evidence of PDF validity or browser rendering.
    result = await ChromiumPdfWorker(runtime).render(DOC)
    assert result == b"%PDF-1.7 fixture"
    assert runtime.jobs[0].closed
    assert runtime.jobs[0].processes[0].returncode == 0
    assert not runtime.jobs[0].path.exists()


async def test_html_preparation_runs_off_loop_and_settles_cancellation(runtime, monkeypatch):
    main_thread = threading.get_ident()
    started = threading.Event()
    release = threading.Event()

    def prepare_html(document):
        assert threading.get_ident() != main_thread
        started.set()
        release.wait(5)
        return b"<html></html>"

    monkeypatch.setattr(chromium, "render_print_html", prepare_html)
    task = asyncio.create_task(ChromiumPdfWorker(runtime).render(DOC))
    assert await asyncio.to_thread(started.wait, 2)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert runtime.jobs == []


@pytest.mark.parametrize("outcome", ["cancel", "deadline", "delayed_spawn"])
async def test_cancel_and_deadline_reap_spawned_process(runtime, monkeypatch, outcome):
    entered, release = asyncio.Event(), asyncio.Event()

    async def spawn(directory):
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-c",
            "import time; time.sleep(20)",
            cwd=directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        runtime.jobs[-1].processes.append(process)
        entered.set()
        if outcome == "delayed_spawn":
            await release.wait()
        return process

    monkeypatch.setattr(chromium, "_spawn", spawn)
    task = asyncio.create_task(
        ChromiumPdfWorker(runtime, timeout=0.1 if outcome == "deadline" else 5).render(DOC)
    )
    await entered.wait()
    if outcome != "deadline":
        task.cancel()
    release.set()
    with pytest.raises(InvalidRequest if outcome == "deadline" else asyncio.CancelledError):
        await task
    assert runtime.jobs[0].closed and runtime.jobs[0].processes[0].returncode is not None
    assert not runtime.jobs[0].path.exists()


async def test_cleanup_failure_disables_worker_and_hides_raw_error(runtime):
    prepare = runtime.prepare

    def failing(directory):
        job = prepare(directory)
        job.fail = True
        return job

    runtime.prepare = failing
    worker = ChromiumPdfWorker(runtime)
    with pytest.raises(InvalidRequest, match="operator recovery"):
        await worker.render(DOC)
    with pytest.raises(InvalidRequest, match="operator recovery"):
        await worker.render(DOC)
    assert len(runtime.jobs) == 1
    assert runtime.jobs[0].path.exists()
    shutil.rmtree(runtime.jobs[0].path)


@pytest.mark.parametrize(
    "receipt",
    [
        {"pages": 129, "bytes": 16},
        {"pages": True, "bytes": 16},
        {"pages": 1, "bytes": 99},
        {"pages": 1, "bytes": True},
        {"pages": 1, "bytes": 16, "other": 0},
    ],
)
async def test_output_receipts_fail_closed(receipt):
    stream = asyncio.StreamReader()
    stream.feed_data(json.dumps(receipt).encode() + b"\n%PDF-1.7 fixture")
    stream.feed_eof()
    with pytest.raises(ValueError):
        await ChromiumPdfWorker._result(stream)


def test_platform_policy_fails_closed_and_keeps_chromium_sandbox(monkeypatch, tmp_path):

    policy = LinuxChromiumPolicy(
        tmp_path, "/usr/bin/chromium", "a" * 64, tmp_path / "bwrap", "b" * 64, tmp_path
    )
    monkeypatch.setattr(chromium_runtime.sys, "platform", "win32")
    with pytest.raises(InvalidRequest, match="Linux isolation"):
        policy.prepare(tmp_path)
    command = policy.command(tmp_path)
    assert "--unshare-net" in command and "--unshare-pid" in command
    assert "--ro-bind" in command and "--no-sandbox" not in command
    assert "--bind" not in command
    assert command.count("--size") == 2
    assert command.count(str(64 * 1024 * 1024)) == 2
    assert str(tmp_path / "input.html") in command


async def test_failed_cleanup_retains_slot_and_live_descendant_workspace(runtime, monkeypatch):
    slots = threading.BoundedSemaphore(2)
    monkeypatch.setattr(async_documents, "_SLOTS", slots)
    entered = asyncio.Event()
    descendant = None

    async def spawn(directory):
        nonlocal descendant
        descendant = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-c",
            "import time; time.sleep(20)",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        async def failed_close():
            raise OSError("cgroup kill failed before descendant termination")

        runtime.jobs[-1].close = failed_close
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-c",
            "import time; time.sleep(20)",
            cwd=directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        runtime.jobs[-1].processes.append(process)
        entered.set()
        return process

    monkeypatch.setattr(chromium, "_spawn", spawn)
    renderer = async_documents.AsyncReportDocumentRenderer(worker=ChromiumPdfWorker(runtime))
    task = asyncio.create_task(renderer.render(DOC, ExportFormat.PDF))
    await entered.wait()
    task.cancel()
    try:
        with pytest.raises(RenderCleanupFailed):
            await task
        assert descendant is not None and descendant.returncode is None
        assert runtime.jobs[0].path.exists()
        assert runtime.jobs[0].processes[0].returncode is not None
        assert slots.acquire(blocking=False)
        assert not slots.acquire(blocking=False)
    finally:
        if descendant is not None:
            descendant.kill()
            await descendant.wait()
        directory = runtime.jobs[0].path
        assert directory.parent == Path(tempfile.gettempdir()).resolve()
        assert directory.name.startswith("ase-pdf-")
        shutil.rmtree(directory)


async def test_noisy_owned_worker_rejection_reaps_without_pipe_deadlock(runtime, monkeypatch):
    async def spawn(directory):
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-c",
            "import sys,time; sys.stdout.buffer.write(b'x'*1000000); "
            "sys.stdout.flush(); time.sleep(20)",
            cwd=directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        runtime.jobs[-1].processes.append(process)
        return process

    monkeypatch.setattr(chromium, "_spawn", spawn)

    # Fake cgroup termination only kills; worker is responsible for pipe draining/reaping.
    def prepare(directory):
        job = Job(directory)

        async def close():
            for process in job.processes:
                if process.returncode is None:
                    process.kill()
            job.closed = True

        job.close = close
        runtime.jobs.append(job)
        return job

    runtime.prepare = prepare
    with pytest.raises(InvalidRequest):
        await asyncio.wait_for(ChromiumPdfWorker(runtime).render(DOC), 3)
    assert runtime.jobs[0].processes[0].returncode is not None
    assert not runtime.jobs[0].path.exists()
