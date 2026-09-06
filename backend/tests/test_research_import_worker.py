"""The untrusted parser is a real bounded child, and every failure reaps it."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from ase.adapters.research_imports import extract_upload
from ase.adapters.research_imports import runner as module
from ase.adapters.research_imports.models import ImportRejected
from ase.adapters.research_imports.runner import DocumentImportRunner
from ase.adapters.research_imports.worker_protocol import validate_result


async def test_real_isolated_worker_imports_and_applies_platform_limits() -> None:
    result = await DocumentImportRunner().run(b"First\nSecond", "notes.txt")
    assert [unit.reference for unit in result.units] == ["line 1", "line 2"]
    assert result.sha256 == hashlib.sha256(b"First\nSecond").hexdigest()


async def test_real_worker_errors_do_not_disclose_input() -> None:
    with pytest.raises(ImportRejected, match="failed or exceeded") as error:
        await DocumentImportRunner().run(b"%PDF-SECRET-CONTENT", "private.pdf")
    assert "SECRET" not in str(error.value)
    assert "private.pdf" not in str(error.value)


async def test_real_media_worker_returns_bounded_preview_and_metadata() -> None:
    output = io.BytesIO()
    Image.new("RGB", (32, 32), "red").save(output, format="PNG")
    result = await DocumentImportRunner().run_media(output.getvalue(), "sample.png")
    assert result.media_type == "image/png"
    assert len(result.frames) == 1 and result.frames[0].png.startswith(b"\x89PNG")
    assert result.sha256 == hashlib.sha256(output.getvalue()).hexdigest()
    assert any("OCR" in limitation for limitation in result.limitations)


def test_real_child_cannot_allocate_beyond_required_memory_budget() -> None:
    script = (
        "from ase.adapters.research_worker.limits import apply_resource_limits\n"
        "apply_resource_limits()\n"
        "try:\n"
        "    payload = bytearray(550 * 1024 * 1024)\n"
        "except MemoryError:\n"
        "    print('memory limited')\n"
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        timeout=10,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == b"memory limited"


class FakeProcess:
    def __init__(self, *, finished: bool = False) -> None:
        self.returncode: int | None = 0 if finished else None
        self.killed = False
        self.waited = False
        self.complete = asyncio.Event()
        if finished:
            self.complete.set()

    async def wait(self) -> int:
        await self.complete.wait()
        self.waited = True
        assert self.returncode is not None
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        self.returncode = -1
        self.complete.set()


def patch_processes(
    monkeypatch: pytest.MonkeyPatch, *, finished: bool = False
) -> tuple[list[FakeProcess], list[Path], asyncio.Event]:
    processes: list[FakeProcess] = []
    directories: list[Path] = []
    spawned = asyncio.Event()

    async def spawn(directory: Path) -> FakeProcess:
        directories.append(directory)
        process = FakeProcess(finished=finished)
        processes.append(process)
        spawned.set()
        return process

    monkeypatch.setattr(module, "_spawn", spawn)
    monkeypatch.setattr(module, "_kill_process_tree", lambda process: process.kill())
    return processes, directories, spawned


async def test_timeout_kills_waits_and_removes_owned_temporary_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processes, directories, _ = patch_processes(monkeypatch)
    service = DocumentImportRunner(timeout=0.01)
    with pytest.raises(ImportRejected, match="time limit"):
        await service.run(b"content", "notes.txt")
    assert processes[0].killed and processes[0].waited
    assert not directories[0].exists()
    assert service._active == 0


async def test_cancellation_reaps_child_before_return_and_releases_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processes, directories, spawned = patch_processes(monkeypatch)
    service = DocumentImportRunner()
    task = asyncio.create_task(service.run(b"content", "notes.txt"))
    await spawned.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert processes[0].killed and processes[0].waited
    assert not directories[0].exists()
    assert service._active == 0


async def test_third_import_is_rejected_without_queue_or_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processes, directories, spawned = patch_processes(monkeypatch)
    service = DocumentImportRunner()
    first = asyncio.create_task(service.run(b"a", "a.txt"))
    await spawned.wait()
    spawned.clear()
    second = asyncio.create_task(service.run(b"b", "b.txt"))
    await spawned.wait()
    with pytest.raises(ImportRejected, match="busy"):
        await service.run(b"c", "c.txt")
    assert len(processes) == 2
    first.cancel()
    second.cancel()
    await asyncio.gather(first, second, return_exceptions=True)
    assert all(process.killed and process.waited for process in processes)
    assert all(not directory.exists() for directory in directories)


@pytest.mark.parametrize(
    "output",
    [None, b"{bad", b"x" * (module.MAX_OUTPUT_BYTES + 1)],
    ids=["missing", "malformed", "oversized"],
)
async def test_missing_invalid_or_oversized_response_cleans_up(
    monkeypatch: pytest.MonkeyPatch, output: bytes | None
) -> None:
    process = FakeProcess(finished=True)
    directories: list[Path] = []

    async def spawn(directory: Path) -> FakeProcess:
        directories.append(directory)
        if output is not None:
            (directory / "result.json").write_bytes(output)
        return process

    monkeypatch.setattr(module, "_spawn", spawn)
    monkeypatch.setattr(module, "_kill_process_tree", lambda _: None)
    with pytest.raises(ImportRejected):
        await DocumentImportRunner().run(b"source", "notes.txt")
    assert process.waited and not directories[0].exists()


def payload() -> dict[str, Any]:
    return {"ok": True, "result": asdict(extract_upload(b"text", "a.txt"))}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("filename", "other.txt"),
        ("sha256", "0" * 64),
        ("media_type", "text/html"),
        ("units", []),
        ("units", [{"reference": "line 1", "text": "x" * 1_801}]),
        ("units", [{"reference": "same", "text": "x"}] * 2),
        ("limitations", []),
        ("limitations", ["x" * 501]),
        ("limitations", [3]),
    ],
    ids=lambda value: value if isinstance(value, str) and len(value) < 50 else type(value).__name__,
)
def test_parent_rejects_worker_provenance_and_budget_violations(field: str, value: object) -> None:
    response = payload()
    response["result"][field] = value
    with pytest.raises(ImportRejected):
        validate_result(json.dumps(response).encode(), "a.txt", hashlib.sha256(b"text").hexdigest())


def test_unavailable_os_limits_fail_closed() -> None:
    with pytest.raises(ImportRejected, match="resource limits are unavailable"):
        validate_result(b'{"ok":false,"error":"resource_limits"}', "a.txt", "hash")


@pytest.mark.parametrize("timeout", [0, -1, 31, float("nan"), float("inf")])
def test_timeout_cannot_disable_or_exceed_deadline(timeout: float) -> None:
    with pytest.raises(ValueError):
        DocumentImportRunner(timeout)


async def test_cancellation_during_os_spawn_still_reaps_eventual_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess()
    started = asyncio.Event()
    release = asyncio.Event()
    directories: list[Path] = []

    async def spawn(directory: Path) -> FakeProcess:
        directories.append(directory)
        started.set()
        await release.wait()
        return process

    monkeypatch.setattr(module, "_spawn", spawn)
    monkeypatch.setattr(module, "_kill_process_tree", lambda child: child.kill())
    task = asyncio.create_task(DocumentImportRunner().run(b"text", "a.txt"))
    await started.wait()
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert process.killed and process.waited
    assert not directories[0].exists()


@pytest.mark.parametrize(
    "response",
    [
        b"{bad",
        b"{}",
        b'{"ok":true,"ok":false}',
        b'{"ok":1}',
        b'{"ok":true,"result":{}}',
        b"[" * 33,
    ],
)
def test_parent_rejects_ambiguous_or_deep_worker_json(response: bytes) -> None:
    with pytest.raises(ImportRejected):
        validate_result(response, "a.txt", "hash")


async def test_spawn_failure_releases_admission_and_tempfiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directories: list[Path] = []

    async def fail(directory: Path) -> FakeProcess:
        directories.append(directory)
        raise OSError("sensitive path")

    monkeypatch.setattr(module, "_spawn", fail)
    service = DocumentImportRunner()
    with pytest.raises(ImportRejected, match="could not run safely"):
        await service.run(b"text", "a.txt")
    assert service._active == 0 and not directories[0].exists()
