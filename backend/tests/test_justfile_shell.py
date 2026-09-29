"""The Justfile's Windows shell must parse its fail-fast recipe syntax."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows shell compatibility")
def test_windows_justfile_shell_supports_fail_fast_chaining() -> None:
    justfile = Path(__file__).resolve().parents[2] / "Justfile"
    match = re.search(r"^set windows-shell := (\[.*\])$", justfile.read_text(), re.MULTILINE)
    assert match is not None
    shell = json.loads(match.group(1))

    successful = subprocess.run(  # noqa: S603 - repository-owned shell, fixed probe
        [*shell, "Write-Output first && Write-Output second"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert successful.returncode == 0, successful.stderr
    assert successful.stdout.splitlines() == ["first", "second"]

    failed = subprocess.run(  # noqa: S603 - repository-owned shell, fixed probe
        [*shell, "Write-Error stop && Write-Output second"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert failed.returncode != 0
    assert "second" not in failed.stdout
