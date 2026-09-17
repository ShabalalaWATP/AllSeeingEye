"""Run one deterministic backend test shard with coverage for later aggregation.

Usage (inside backend): uv run python ../scripts/run_test_shard.py INDEX COUNT
INDEX is zero-based. Each CI shard must have its own disposable database because
the application fixtures drop and recreate the schema. Do not share one database
between concurrent shards. Combine coverage separately for each database backend
and enforce the project's 90% gate after every shard succeeds.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"


def test_files(backend: Path) -> list[str]:
    """Match pytest's default Python file patterns in its configured tests root."""
    return sorted(
        path.relative_to(backend).as_posix()
        for path in (backend / "tests").rglob("*.py")
        if path.name.startswith("test_") or path.name.endswith("_test.py")
    )


def select_shard(files: list[str], index: int, count: int) -> list[str]:
    """Round-robin complete files so each fixture remains within a single job."""
    if count < 1 or not 0 <= index < count:
        raise ValueError("COUNT must be positive and INDEX must be between 0 and COUNT - 1")
    return sorted(files)[index::count]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=int)
    parser.add_argument("count", type=int)
    args = parser.parse_args(argv)
    try:
        files = select_shard(test_files(BACKEND), args.index, args.count)
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
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "--cov-fail-under=0", "--cov-report=", *files],
        cwd=BACKEND,
        env=environment,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
