"""Opt-in controller-only phase reports, without inspecting test or fixture values."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--record-test-phases",
        metavar="PATH",
        help="Write fresh controller TestReport JSONL, retaining partial failed sessions.",
    )


def pytest_configure(config: pytest.Config) -> None:
    target = config.getoption("--record-test-phases")
    # xdist forwards worker reports to the controller. Workers must not open the
    # shared output or register a second writer for those same reports.
    if not target or hasattr(config, "workerinput"):
        return
    try:
        recorder = PhaseRecorder(Path(target))
    except OSError as error:
        raise pytest.UsageError("Phase telemetry requires a new writable output file") from error
    config.add_cleanup(recorder.close)
    config.pluginmanager.register(recorder, "ase-test-phases")


class PhaseRecorder:
    """Preserve existing pytest timings; no additional timers or execution hooks."""

    def __init__(self, target: Path) -> None:
        # Refuse to overwrite an earlier attempt, including incomplete evidence.
        # Line buffering retains completed reports if pytest later fails or exits.
        self.stream: TextIO = target.open("x", encoding="utf-8", newline="\n", buffering=1)
        self.reports = 0

    def write(self, value: dict[str, object]) -> None:
        self.stream.write(json.dumps(value, allow_nan=False) + "\n")

    def pytest_sessionstart(self) -> None:
        self.write({"event": "session_start", "schema_version": 1})

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        record: dict[str, object] = {
            "event": "phase",
            "nodeid": report.nodeid,
            "phase": report.when,
            "duration": report.duration,
            "outcome": report.outcome,
        }
        worker = getattr(report, "worker_id", None)
        if isinstance(worker, str):
            record["worker_id"] = worker
        self.write(record)
        self.reports += 1

    def pytest_sessionfinish(self, exitstatus: int) -> None:
        self.write(
            {"event": "session_finish", "exitstatus": int(exitstatus), "reports": self.reports}
        )
        self.close()

    def close(self) -> None:
        self.stream.close()
