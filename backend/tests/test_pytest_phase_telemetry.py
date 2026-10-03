"""Reporting preserves phase identities and partial evidence without test payloads."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pytest_phase_telemetry import PhaseRecorder, pytest_configure


def report(when: str = "call", outcome: str = "passed") -> pytest.TestReport:
    return pytest.TestReport(
        "tests/test_example.py::test_case[original-id]",
        ("tests/test_example.py", 10, "test_case"),
        keywords={},
        outcome=outcome,
        longrepr="private exception payload",
        when=when,
        duration=0.000123456789,
        sections=[("captured stdout", "private output")],
        user_properties=[("secret", "private value")],
    )


def records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_raw_phases_keep_only_permitted_fields_and_actual_worker(tmp_path):
    path = tmp_path / "parallel.controller.jsonl"
    recorder = PhaseRecorder(path)
    try:
        recorder.pytest_sessionstart()
        for when, outcome in (("setup", "passed"), ("call", "failed"), ("teardown", "passed")):
            item = report(when, outcome)
            item.worker_id = "gw2"
            recorder.pytest_runtest_logreport(item)
        # Every complete line is readable before close/session completion.
        phases = records(path)[1:]
        assert [item["phase"] for item in phases] == ["setup", "call", "teardown"]
        assert all(item["worker_id"] == "gw2" for item in phases)
        assert phases[1] == {
            "event": "phase",
            "nodeid": item.nodeid,
            "phase": "call",
            "duration": 0.000123456789,
            "outcome": "failed",
            "worker_id": "gw2",
        }
        assert "private" not in path.read_text()
        recorder.pytest_sessionfinish(1)
        assert records(path)[-1] == {"event": "session_finish", "exitstatus": 1, "reports": 3}
    finally:
        recorder.close()


def test_interrupted_session_keeps_partial_evidence_without_inventing_worker(tmp_path):
    path = tmp_path / "serial.controller.jsonl"
    recorder = PhaseRecorder(path)
    recorder.pytest_sessionstart()
    recorder.pytest_runtest_logreport(report("setup", "skipped"))
    recorder.close()  # Session finish never occurred, as with an interrupted controller.
    saved = records(path)
    assert len(saved) == 2
    assert saved[-1]["outcome"] == "skipped"
    assert "worker_id" not in saved[-1]
    assert not any(row["event"] == "session_finish" for row in saved)
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        PhaseRecorder(path)
    assert path.read_bytes() == original


@pytest.mark.parametrize("enabled,worker", [(False, False), (True, True)])
def test_disabled_and_worker_processes_never_create_output(tmp_path, enabled, worker):
    path = tmp_path / "phases.jsonl"
    config = SimpleNamespace(
        getoption=lambda _name: str(path) if enabled else None,
        add_cleanup=Mock(),
        pluginmanager=Mock(),
    )
    if worker:
        config.workerinput = {"workerid": "gw0"}
    pytest_configure(config)
    assert not path.exists()
    config.add_cleanup.assert_not_called()
    config.pluginmanager.register.assert_not_called()


def test_controller_registers_one_writer_and_cleanup_preserves_partial(tmp_path):
    path = tmp_path / "phases.jsonl"
    config = SimpleNamespace(
        getoption=lambda _name: str(path), add_cleanup=Mock(), pluginmanager=Mock()
    )
    pytest_configure(config)
    recorder, name = config.pluginmanager.register.call_args.args
    assert name == "ase-test-phases"
    recorder.pytest_runtest_logreport(report("setup", "failed"))
    config.add_cleanup.call_args.args[0]()
    assert records(path)[0]["outcome"] == "failed"
    with pytest.raises(pytest.UsageError, match="new writable output"):
        pytest_configure(config)
    assert len(records(path)) == 1


@pytest.mark.parametrize("workers", [None, "2"])
def test_real_pytest_sessions_keep_every_emitted_phase_once(tmp_path, workers):
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (tmp_path / "test_sample.py").write_text("""import pytest
@pytest.mark.parametrize("value", [1, 2])
def test_success(value):
    assert value > 0
@pytest.fixture
def bad_setup():
    raise ValueError("private setup detail")
def test_setup_failure(bad_setup):
    raise AssertionError("unreachable")
@pytest.fixture
def bad_teardown():
    yield
    raise ValueError("private finalizer detail")
def test_teardown_failure(bad_teardown):
    pass
@pytest.mark.skip(reason="offline skip")
def test_skip():
    pass
def test_call_failure():
    assert False, "private assertion detail"
""")
    output = tmp_path / "phases.controller.jsonl"
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("ASE_", "PG", "PYTEST_", "COVERAGE_", "COV_CORE_", "_COV_CORE_"))
        and key != "DATABASE_URL"
    }
    env["PYTHONPATH"] = str(Path(__file__).parent)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-c",
        "pytest.ini",
        "-q",
        "-p",
        "no:cacheprovider",
        "-p",
        "pytest_phase_telemetry",
        "--record-test-phases=" + str(output),
    ]
    if workers:
        command += ["-n", workers, "--max-worker-restart=0"]
    # Only this interpreter, the fixed pytest arguments and our private fixture are used.
    result = subprocess.run(  # noqa: S603
        command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=45, check=False
    )
    assert result.returncode == 1, result.stdout + result.stderr
    saved = records(output)
    phases = [row for row in saved if row["event"] == "phase"]
    assert saved[0] == {"event": "session_start", "schema_version": 1}
    assert saved[-1] == {"event": "session_finish", "exitstatus": 1, "reports": 16}
    assert len(phases) == len({(row["nodeid"], row["phase"]) for row in phases}) == 16
    assert len({row["nodeid"] for row in phases}) == 6
    assert {row["phase"] for row in phases} == {"setup", "call", "teardown"}
    assert any(row["phase"] == "setup" and row["outcome"] == "failed" for row in phases)
    assert any(row["phase"] == "teardown" and row["outcome"] == "failed" for row in phases)
    assert any(row["outcome"] == "skipped" for row in phases)
    assert all(isinstance(row["duration"], float) and row["duration"] >= 0 for row in phases)
    assert all(("worker_id" in row) == bool(workers) for row in phases)
    if workers:
        assert {row["worker_id"] for row in phases} == {"gw0", "gw1"}
    assert "private" not in output.read_text()
