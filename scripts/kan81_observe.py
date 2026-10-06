"""One baseline then candidate, original uninstrumented canonical benchmark."""

import argparse
import json
import math
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

from kan81_inputs import (
    BASELINE,
    BENCHMARK,
    CANDIDATE,
    host,
    installed,
    prepare_sources,
    sha,
    sources,
)
from kan81_process import clean_env, dump, run_owned, utc


def benchmark_command(node: Path) -> list[str]:
    return [
        str(node),
        "node_modules/vitest/vitest.mjs",
        "run",
        BENCHMARK,
        "--maxWorkers=1",
        "--no-coverage",
    ]


def metrics(text: str) -> dict:
    records = [
        json.loads(line)["kan81"]
        for line in text.splitlines()
        if line.startswith('{"kan81":')
    ]
    if (
        len(records) != 1
        or not re.search(r"Tests\s+1 passed\s+\(1\)", text)
        or not re.search(r"Test Files\s+1 passed\s+\(1\)", text)
    ):
        raise ValueError("One completed canonical test and metrics record required")
    record = records[0]
    if set(record) != {"newIds", "existingIds", "mixed", "controlLatency"}:
        raise ValueError("Scenario census differs")
    for name, values in record.items():
        fields = (
            {"medianMs", "maxMs"}
            if name == "controlLatency"
            else {
                "totalMedianMs",
                "totalMaxMs",
                "mergeMedianMs",
                "reactMedianMs",
                "profilerMedianMs",
                "commitsPerBatch",
            }
        )
        if set(values) != fields or any(
            type(value) not in (int, float) or not math.isfinite(value) or value < 0
            for value in values.values()
        ):
            raise ValueError("Invalid metrics")
        median, maximum = (
            ("medianMs", "maxMs")
            if name == "controlLatency"
            else ("totalMedianMs", "totalMaxMs")
        )
        if values[median] > values[maximum]:
            raise ValueError("Median exceeds maximum")
    return record


def targets(record: dict) -> bool:
    return all(
        values["medianMs" if name == "controlLatency" else "totalMedianMs"] <= 20
        and values["maxMs" if name == "controlLatency" else "totalMaxMs"] < 50
        for name, values in record.items()
    )


def observe(arms: dict[str, Path], node: Path, envs: dict, output: Path) -> dict:
    observations = {}
    for name, root in arms.items():
        run_owned(
            benchmark_command(node), root / "frontend", envs[name], output, name, 180
        )
        observations[name] = metrics(
            (output / f"{name}.log").read_text(encoding="utf-8")
        )
        dump(output / f"{name}-metrics.json", observations[name])
    return observations


def interrupt(_signum, _frame):
    raise InterruptedError("Observation interrupted")


def readback(arms, input_record, inventories, node, pnpm, runtime, controls) -> dict:
    """Attempt all available witnesses, including after failed preparation or tests."""
    checks = {}
    for name, root in arms.items():
        for kind, before, reader in (
            ("source", input_record.get(name), lambda root=root: sources(root)),
            (
                "dependencies",
                inventories.get(name),
                lambda root=root: installed(root / "frontend"),
            ),
        ):
            label = f"{name}-{kind}"
            if before is None:
                checks[label] = {"verified": False, "unavailable": "not prepared"}
                continue
            try:
                checks[label] = {"verified": reader() == before}
            except (
                OSError,
                ValueError,
                RuntimeError,
                subprocess.SubprocessError,
            ) as error:
                checks[label] = {"verified": False, "errorClass": type(error).__name__}
    try:
        checks["runtime"] = {
            "verified": {"node": sha(node), "pnpm": sha(pnpm)} == runtime
        }
    except (OSError, ValueError) as error:
        checks["runtime"] = {"verified": False, "errorClass": type(error).__name__}
    try:
        checks["controls"] = {
            "verified": bool(controls)
            and all(sha(Path(path)) == pin for path, pin in controls.items())
        }
    except (OSError, ValueError) as error:
        checks["controls"] = {"verified": False, "errorClass": type(error).__name__}
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "candidate", "runtime", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "linux" or os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise RuntimeError("First-attempt Linux CI observation only")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    dump(
        output / "claim.json",
        {"started": utc(), "baseline": BASELINE, "candidate": CANDIDATE},
    )
    result = {"completed": False, "stage": "inputs", "observations": {}}
    node = args.runtime.resolve() / "node/bin/node"
    pnpm = args.runtime.resolve() / "pnpm/bin/pnpm.mjs"
    arms = {"baseline": args.baseline.resolve(), "candidate": args.candidate.resolve()}
    previous = signal.signal(signal.SIGTERM, interrupt)
    input_record, inventories, runtime, controls = {}, {}, {}, {}
    failure = None
    try:
        scripts = Path(__file__).resolve().parent
        control_paths = [
            scripts / name
            for name in ("kan81_observe.py", "kan81_inputs.py", "kan81_process.py")
        ]
        control_paths.append(scripts.parent / ".github/workflows/kan81-reference.yml")
        controls = {str(path): sha(path) for path in control_paths}
        dump(output / "controls.json", controls)
        input_record = prepare_sources(arms["baseline"], arms["candidate"])
        runtime = {"node": sha(node), "pnpm": sha(pnpm)}
        dump(output / "inputs.json", input_record)
        dump(
            output / "host.json",
            {
                **host(),
                "imageOS": os.environ.get("ImageOS"),
                "imageVersion": os.environ.get("ImageVersion"),
                "runId": os.environ.get("GITHUB_RUN_ID"),
                "workflowSHA": os.environ.get("GITHUB_WORKFLOW_SHA"),
                "runtime": runtime,
            },
        )
        envs = {}
        for name in arms:
            envs[name] = clean_env(
                output / f"{name}-home", output / f"{name}-tmp", node
            )
        for name, command, expected in (
            ("node-version", [str(node), "--version"], "v24.19.0"),
            ("pnpm-version", [str(node), str(pnpm), "--version"], "11.25.0"),
        ):
            run_owned(command, output, envs["baseline"], output, name, 30)
            if (output / f"{name}.log").read_text().strip() != expected:
                raise RuntimeError("Runtime version differs")
        result["stage"] = "install"
        for name, root in arms.items():
            run_owned(
                [
                    str(node),
                    str(pnpm),
                    "install",
                    "--frozen-lockfile",
                    "--store-dir",
                    str(output / f"{name}-store"),
                ],
                root / "frontend",
                envs[name],
                output,
                f"{name}-install",
                600,
            )
        for name, root in arms.items():
            inventories[name] = installed(root / "frontend")
        dump(output / "dependencies.json", inventories)
        if inventories["baseline"] != inventories["candidate"]:
            raise RuntimeError("Installed dependency inventories differ")
        for name, root in arms.items():
            if sources(root) != input_record[name]:
                raise RuntimeError("Install changed tracked frontend")
        result["stage"] = "observation"
        result["observations"] = observe(arms, node, envs, output)
        result["stage"] = "readback"
        result["candidateTargetsMet"] = targets(result["observations"]["candidate"])
    except BaseException as error:  # noqa: BLE001 - retain evidence, then re-raise.
        failure = error
        result["failureClass"] = type(error).__name__
    finally:
        checks = readback(
            arms, input_record, inventories, node, pnpm, runtime, controls
        )
        dump(output / "readback.json", checks)
        result["completed"] = failure is None and all(
            row["verified"] for row in checks.values()
        )
        signal.signal(signal.SIGTERM, previous)
        result["finished"] = utc()
        dump(output / "result.json", result)
    if failure is not None:
        raise failure
    if not result["completed"]:
        raise RuntimeError("Input readback failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
