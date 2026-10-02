"""Shard report suppression keeps branch data and the default coverage failure gate."""

import os
import subprocess
import sys
from pathlib import Path

from coverage import Coverage, CoverageData


def invoke(project, data_file, *arguments):
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("ASE_", "COVERAGE_", "COV_CORE_", "_COV_CORE_", "PYTEST_"))
    }
    environment.update(COVERAGE_FILE=str(data_file), PYTHONPATH=str(project))
    # Execute only this interpreter and the controlled private fixture project.
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", *arguments],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


def measured_arcs(path):
    data = CoverageData(basename=str(path))
    data.read()
    assert data.has_arcs()
    return {name: sorted(data.arcs(name) or []) for name in data.measured_files()}


def test_quiet_shards_retain_raw_branches_and_combined_negative_gate(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    configuration = tmp_path / "pyproject.toml"
    configuration.write_text((backend / "pyproject.toml").read_text(encoding="utf-8"))
    package = tmp_path / "ase"
    package.mkdir()
    (package / "__init__.py").write_text(
        'def choose(flag):\n    if flag:\n        return "observed"\n    return "unobserved"\n'
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_branch.py").write_text(
        'from ase import choose\n\ndef test_observed():\n    assert choose(True) == "observed"\n'
    )
    ordinary_data = tmp_path / "ordinary.coverage"
    shard_data = tmp_path / "shard.coverage"
    ordinary = invoke(tmp_path, ordinary_data, "pytest", "-q")
    assert ordinary.returncode == 1, ordinary.stdout + ordinary.stderr
    assert "1 passed" in ordinary.stdout
    assert "Missing" in ordinary.stdout
    assert "Required test coverage of 90% not reached" in ordinary.stdout

    # These are the existing shard options; only the combined job enforces the floor.
    shard = invoke(tmp_path, shard_data, "pytest", "-q", "--cov-report=", "--cov-fail-under=0")
    assert shard.returncode == 0, shard.stdout + shard.stderr
    assert "1 passed" in shard.stdout
    ordinary_arcs = measured_arcs(ordinary_data)
    assert {Path(name).resolve() for name in ordinary_arcs} == {(package / "__init__.py").resolve()}
    assert measured_arcs(shard_data) == ordinary_arcs

    combined_data = tmp_path / "combined.coverage"
    combined = Coverage(data_file=str(combined_data), config_file=str(configuration))
    combined.combine(data_paths=[str(ordinary_data), str(shard_data)], keep=True)
    combined.save()
    assert measured_arcs(combined_data) == ordinary_arcs
    negative = invoke(tmp_path, combined_data, "coverage", "report", "--fail-under=90")
    assert negative.returncode == 2, negative.stdout + negative.stderr
    assert "fail-under=90" in negative.stdout
    assert "tests coverage" not in shard.stdout
    assert "TOTAL" not in shard.stdout
