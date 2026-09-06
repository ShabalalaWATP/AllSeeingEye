"""Worker boot refuses missing OS limits and only parses the fixed JSON protocol."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ase.adapters.research_worker import __main__ as worker
from ase.adapters.research_worker import limits


def test_windows_job_has_memory_and_descendant_cleanup_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = MagicMock()
    kernel.CreateJobObjectW.return_value = 42
    kernel.SetInformationJobObject.return_value = True
    kernel.AssignProcessToJobObject.return_value = True
    monkeypatch.setattr(limits.ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)
    limits._windows_limits()
    configured = kernel.SetInformationJobObject.call_args.args[2]._obj
    assert configured.BasicLimitInformation.LimitFlags == 0x2300
    assert configured.ProcessMemoryLimit == configured.JobMemoryLimit == 512 * 1024 * 1024
    kernel.AssignProcessToJobObject.assert_called_once()
    kernel.CloseHandle.assert_not_called()


@pytest.mark.parametrize("failure", ["create", "configure", "assign"])
def test_windows_job_configuration_failure_refuses_parser_start(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    kernel = MagicMock()
    kernel.CreateJobObjectW.return_value = None if failure == "create" else 42
    kernel.SetInformationJobObject.return_value = failure != "configure"
    kernel.AssignProcessToJobObject.return_value = failure != "assign"
    monkeypatch.setattr(limits.ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)
    with pytest.raises(limits.ResourceLimitUnavailable):
        limits._windows_limits()
    if failure != "create":
        kernel.CloseHandle.assert_called_once_with(42)


def test_posix_memory_and_core_dump_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    resources = SimpleNamespace(RLIMIT_AS=9, RLIMIT_CORE=4, setrlimit=MagicMock())
    monkeypatch.setattr(limits, "os", SimpleNamespace(name="posix"))
    monkeypatch.setattr(limits, "importlib", SimpleNamespace(import_module=lambda _: resources))
    limits.apply_resource_limits()
    assert resources.setrlimit.call_args_list[0].args == (9, (limits.MEMORY_BYTES,) * 2)
    assert resources.setrlimit.call_args_list[1].args == (4, (0, 0))
    resources.setrlimit.side_effect = OSError("host internals")
    with pytest.raises(limits.ResourceLimitUnavailable):
        limits.apply_resource_limits()


def test_unknown_platform_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(limits, "os", SimpleNamespace(name="unsupported"))
    with pytest.raises(limits.ResourceLimitUnavailable):
        limits.apply_resource_limits()


def test_worker_limit_failure_precedes_input_access(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    deny = MagicMock(side_effect=limits.ResourceLimitUnavailable("internal path"))
    monkeypatch.setattr(worker, "apply_resource_limits", deny)
    assert worker.main() == 0
    assert json.loads((tmp_path / "result.json").read_bytes()) == {
        "ok": False,
        "error": "resource_limits",
    }


@pytest.mark.parametrize(
    "worker_request",
    [
        {"mode": "document", "filename": "a.txt"},
        {"mode": "document", "filename": 5},
        {"mode": "arbitrary", "filename": "a.txt"},
        {"mode": "media", "filename": "a.png", "tools": {}},
        {
            "mode": "media",
            "filename": "a.png",
            "tools": {"tesseract": 5, "ffmpeg": None, "ffprobe": None},
        },
        ["wrong"],
        "x" * 2_049,
    ],
    ids=["document", "filename", "mode", "tools", "tool_type", "shape", "oversized"],
)
def test_worker_request_protocol_and_safe_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_request: object
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(worker, "apply_resource_limits", lambda: None)
    (tmp_path / "request.json").write_text(json.dumps(worker_request), encoding="utf-8")
    (tmp_path / "input.bin").write_bytes(b"text")
    assert worker.main() == 0
    response = json.loads((tmp_path / "result.json").read_bytes())
    if worker_request == {"mode": "document", "filename": "a.txt"}:
        assert response["result"]["units"] == [{"reference": "line 1", "text": "text"}]
    else:
        assert response == {"ok": False, "error": "rejected"}


def test_worker_oversized_output_never_hits_the_wire(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    worker._reply({"large": "x" * 100}, maximum=50)
    assert (tmp_path / "result.json").read_bytes() == b'{"ok":false,"error":"rejected"}'
