"""Collect the existing native lanes once, then partition their real selected IDs."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path

from kan81_process import run_owned
from native_shard_manifest import EXPRESSIONS, identity, make_plan, validate_plan

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def collection_command(lane: str, target: Path) -> list[str]:
    isolation = (
        ["--isolated-postgres", "--owned-migrations", "--template-postgres"]
        if lane == "parallel"
        else []
    )
    return [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "--no-cov",
        "-n",
        "0",
        "-o",
        "pythonpath=. tests",
        "-p",
        "owned_postgres",
        *isolation,
        "-m",
        EXPRESSIONS[lane],
        f"--record-nodeids={target}",
        "tests",
    ]


def collection_environment(lane: str) -> dict[str, str]:
    environment = os.environ.copy()
    if lane == "parallel":
        # Match the existing isolated lane: other shared service URLs are forbidden.
        for name in list(environment):
            if name in {"ASE_TOKEN_RACE_TEST_URL", "ASE_ROTATION_TEST_URL"} or (
                name.startswith("ASE_") and name.endswith("_POSTGRES_URL")
            ):
                environment.pop(name)
    return environment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--shards", type=int, choices=range(1, 65), default=4)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output.is_relative_to(ROOT.resolve()):
        parser.error("Planner evidence must be outside the source checkout")
    if sys.platform != "linux":
        parser.error("The bounded native planner requires Linux process groups")
    output.mkdir(parents=True, exist_ok=False)
    result: dict[str, object] = {"completed": False, "stage": "identity", "lanes": {}}
    started = time.monotonic()

    def interrupted(_signum, _frame):
        raise InterruptedError("Native collection interrupted")

    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        before = identity(ROOT)
        lanes = {}
        for lane in EXPRESSIONS:
            result["stage"] = lane
            target = output / f"{lane}-nodeids.txt"
            remaining = 600 - (time.monotonic() - started)
            if remaining < 1:
                raise TimeoutError("Native collection deadline expired")
            receipt = run_owned(
                collection_command(lane, target),
                BACKEND,
                collection_environment(lane),
                output,
                lane,
                min(300, int(remaining)),
            )
            result["lanes"][lane] = {
                "exit_code": receipt["exit"],
                "group_absent": receipt["groupAbsent"],
            }
            lanes[lane] = target.read_text(encoding="utf-8").splitlines()
        if time.monotonic() - started > 600:
            raise TimeoutError("Native collection deadline expired")
        result["stage"] = "source/runtime readback"
        if identity(ROOT) != before:
            raise ValueError("Native inputs changed during planning")
        plan = validate_plan(make_plan(lanes, args.shards, before))
        if time.monotonic() - started > 600:
            raise TimeoutError("Native planning deadline expired before publication")
        with (output / "manifest.json").open("x", encoding="utf-8") as stream:
            json.dump(plan, stream, indent=2, allow_nan=False)
            stream.write("\n")
        result.update(completed=True, stage="complete")
        return 0
    except BaseException as error:  # noqa: BLE001 - retain cancellation after owned cleanup.
        result["error_class"] = type(error).__name__
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)
        result["wall_seconds"] = time.monotonic() - started
        with (output / "result.json").open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
