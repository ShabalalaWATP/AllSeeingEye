"""Run one deterministic backend test shard with coverage for later aggregation.

Usage (inside backend): uv run python ../scripts/run_test_shard.py INDEX COUNT
INDEX is zero-based. Each CI shard must have its own disposable database because
the application fixtures drop and recreate the schema. Do not share one database
between concurrent shards. Combine coverage separately for each database backend
and enforce the project's 90% gate after every shard succeeds.

Whole files are balanced by the per-file seconds in test_durations.json next to this
script; files missing from it count as the median recorded file. Without that file the
shards fall back to round robin. Refresh it from a SQLite run inside backend with
``uv run pytest -n auto --no-cov --record-durations=../scripts/test_durations.json``.

``--workers auto`` runs the shard's files on pytest-xdist workers, each with a private
in-memory SQLite database. The test suite refuses parallel runs against a configured shared
database, so PostgreSQL shards stay serial.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import os
import statistics
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
DURATIONS = Path(__file__).resolve().with_name("test_durations.json")


def test_files(backend: Path) -> list[str]:
    """Match pytest's default Python file patterns in its configured tests root."""
    return sorted(
        path.relative_to(backend).as_posix()
        for path in (backend / "tests").rglob("*.py")
        if path.name.startswith("test_") or path.name.endswith("_test.py")
    )


def load_durations(path: Path) -> dict[str, float]:
    """Recorded seconds per test file; an absent file means no recording yet."""
    if not path.exists():
        return {}
    recorded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(recorded, dict) or not all(
        isinstance(name, str)
        and isinstance(seconds, int | float)
        and not isinstance(seconds, bool)
        and math.isfinite(seconds)
        and seconds >= 0
        for name, seconds in recorded.items()
    ):
        raise ValueError(f"{path.name} must map test files to non-negative seconds")
    return {name: float(seconds) for name, seconds in recorded.items()}


def select_shard(
    files: list[str], index: int, count: int, durations: dict[str, float] | None = None
) -> list[str]:
    """Complete files per shard so each fixture remains within a single job."""
    if count < 1 or not 0 <= index < count:
        raise ValueError("COUNT must be positive and INDEX must be between 0 and COUNT - 1")
    ordered = sorted(files)
    if not durations:
        return ordered[index::count]
    known = [durations[name] for name in ordered if name in durations]
    fallback = statistics.median(known) if known else 1.0
    # Longest first onto the least loaded shard, ties broken by name and shard index,
    # so every job computes the same partition independently.
    weighted = sorted(ordered, key=lambda name: (-durations.get(name, fallback), name))
    loads = [(0.0, shard) for shard in range(count)]
    chosen: list[str] = []
    for name in weighted:
        load, shard = heapq.heappop(loads)
        if shard == index:
            chosen.append(name)
        heapq.heappush(loads, (load + durations.get(name, fallback), shard))
    return sorted(chosen)


def worker_count(value: str) -> str:
    """pytest-xdist's ``auto`` or ``logical``, or a positive number of workers."""
    if value in {"auto", "logical"} or (value.isdecimal() and int(value) > 0):
        return value
    raise argparse.ArgumentTypeError("use auto, logical or a positive number")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=int)
    parser.add_argument("count", type=int)
    parser.add_argument("--workers", type=worker_count, help="pytest-xdist workers per shard")
    args = parser.parse_args(argv)
    try:
        files = select_shard(test_files(BACKEND), args.index, args.count, load_durations(DURATIONS))
    except ValueError as exc:
        parser.error(str(exc))
    if not files:
        parser.error("Shard has no tests; reduce COUNT or check the test directory")

    environment = os.environ.copy()
    environment["COVERAGE_FILE"] = str(BACKEND / f".coverage.shard-{args.index}")
    sys.stdout.write(f"Running shard {args.index + 1}/{args.count}: {len(files)} files\n")
    sys.stdout.flush()
    # The combined CI job enforces coverage. Applying 90% to an individual shard
    # would incorrectly require each subset to exercise the complete application.
    # Fixed Python executable and discovered repository paths, with no shell.
    parallel = ["-n", args.workers] if args.workers else []
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "--cov-fail-under=0", "--cov-report=", *parallel, *files],
        cwd=BACKEND,
        env=environment,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
