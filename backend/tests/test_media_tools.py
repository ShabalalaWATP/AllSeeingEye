"""External tools are bounded subprocesses with safe errors and minimal environment."""

import sys
import time
from pathlib import Path

import pytest

from ase.adapters.research_imports.models import ImportRejected
from ase.adapters.research_media.tools import run_tool, trusted_tool


def test_tool_capture_discards_stderr_and_unrelated_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASE_MEDIA_TEST_SECRET", "synthetic sentinel")
    script = (
        "import os,sys;sys.stderr.write('private stderr');"
        "print(os.getenv('ASE_MEDIA_TEST_SECRET','absent'))"
    )
    assert run_tool([sys.executable, "-I", "-c", script], time.monotonic() + 5).strip() == b"absent"


@pytest.mark.parametrize(
    "script,seconds,limit,reason",
    [
        ("import sys;sys.exit('private failure')", 5, 100, "failed"),
        ("print('x'*10000)", 5, 100, "output exceeds"),
        ("import time;time.sleep(10)", 0.1, 100, "time limit"),
    ],
)
def test_runtime_failures_do_not_echo_commands_or_output(
    script: str, seconds: float, limit: int, reason: str
) -> None:
    with pytest.raises(ImportRejected, match=reason) as error:
        run_tool([sys.executable, "-I", "-c", script], time.monotonic() + seconds, max_output=limit)
    assert "private" not in str(error.value)


def test_expired_deadline_never_launches_tool() -> None:
    with pytest.raises(ImportRejected, match="time limit"):
        run_tool(["not-an-executable"], time.monotonic() - 1)


def test_invalid_runtime_paths_are_rejected_and_missing_runtime_is_unavailable(
    tmp_path: Path,
) -> None:
    assert trusted_tool(None, "ffmpeg") is None
    assert trusted_tool(str(tmp_path / "ffmpeg.exe"), "ffmpeg") is None
    for path in ("ffmpeg", str(tmp_path / "arbitrary.exe")):
        with pytest.raises(ImportRejected, match="trusted executable"):
            trusted_tool(path, "ffmpeg")
    with pytest.raises(ImportRejected, match="could not be started"):
        run_tool([str(tmp_path / "absent.exe")], time.monotonic() + 5)
