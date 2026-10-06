"""Offline planning checks and real two-worker refusal before fixture setup."""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import native_shard_manifest as manifest
import plan_native_shards as planner
import run_test_shard as runner

from scripts.tests.test_native_shard_manifest import inputs


def lanes():
    return {"parallel": ["tests/test_a.py::test_auth"], "serial": ["tests/test_b.py::test_race"]}


class PlannerTests(unittest.TestCase):
    def test_real_lane_commands_keep_authoritative_markers_without_running_tests(self):
        for lane, expression in manifest.EXPRESSIONS.items():
            command = planner.collection_command(lane, Path("ids.txt"))
            self.assertEqual(command[:3], [sys.executable, "-m", "pytest"])
            self.assertIn("--collect-only", command)
            self.assertIn("--no-cov", command)
            self.assertEqual(command[command.index("-n") + 1], "0")
            self.assertEqual(command[command.index("-m", 3) + 1], expression)
            self.assertEqual("--owned-migrations" in command, lane == "parallel")
            self.assertEqual("--template-postgres" in command, lane == "parallel")
            self.assertEqual(command[-1], "tests")
        environment = {
            "ASE_TEST_DATABASE_URL": "loopback",
            "ASE_TOKEN_RACE_TEST_URL": "race",
            "ASE_NOTIFICATION_POSTGRES_URL": "notification",
        }
        with patch.dict(planner.os.environ, environment, clear=True):
            self.assertEqual(
                planner.collection_environment("parallel"), {"ASE_TEST_DATABASE_URL": "loopback"}
            )
            self.assertEqual(planner.collection_environment("serial"), environment)

    def run_planner(self, directory, failure=None, identities=None):
        calls = []

        def collect(command, _cwd, _env, output, lane, seconds):
            calls.append((lane, seconds))
            if failure:
                raise failure
            target = next(
                value.split("=", 1)[1] for value in command if value.startswith("--record-nodeids=")
            )
            Path(target).write_text("\n".join(lanes()[lane]) + "\n", encoding="utf-8")
            return {"exit": 0, "groupAbsent": True}

        with (
            patch.object(planner.sys, "platform", "linux"),
            patch.object(planner, "identity", side_effect=identities or [inputs(), inputs()]),
            patch.object(planner, "run_owned", side_effect=collect),
        ):
            result = planner.main([str(directory), "--shards", "1"])
        return result, calls

    def test_success_only_after_both_lanes_and_final_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result"
            result, calls = self.run_planner(output)
            self.assertEqual(result, 0)
            self.assertEqual([lane for lane, _ in calls], ["parallel", "serial"])
            self.assertTrue(all(0 < seconds <= 300 for _, seconds in calls))
            record = json.loads((output / "result.json").read_text())
            self.assertTrue(record["completed"])
            document = manifest.validate_plan(json.loads((output / "manifest.json").read_text()))
            self.assertEqual(document["lanes"]["parallel"]["ids"], lanes()["parallel"])

    def test_failed_timeout_and_cancelled_collection_never_publish_or_retry(self):
        for failure in (
            RuntimeError("failed"),
            TimeoutError(),
            InterruptedError(),
            KeyboardInterrupt(),
        ):
            with (
                self.subTest(failure=type(failure).__name__),
                tempfile.TemporaryDirectory() as directory,
            ):
                output = Path(directory) / "result"
                result, calls = self.run_planner(output, failure=failure)
                self.assertEqual(result, 1)
                self.assertEqual(len(calls), 1)
                self.assertFalse((output / "manifest.json").exists())
                record = json.loads((output / "result.json").read_text())
                self.assertFalse(record["completed"])
                self.assertEqual(record["error_class"], type(failure).__name__)

    def test_postcollection_source_drift_fails_without_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result"
            changed = inputs()
            changed["source"]["head"] = "d" * 40
            result, calls = self.run_planner(output, identities=[inputs(), changed])
            self.assertEqual(result, 1)
            self.assertEqual(len(calls), 2)
            self.assertFalse((output / "manifest.json").exists())

    def test_existing_evidence_and_in_checkout_output_are_refused(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(planner.sys, "platform", "linux"),
        ):
            with self.assertRaises(FileExistsError):
                planner.main([directory])
            with self.assertRaises(SystemExit), patch.object(planner, "run_owned") as run:
                planner.main([str(planner.ROOT / "forbidden-evidence")])
            run.assert_not_called()

    def test_exhausted_total_budget_does_not_start_the_next_lane(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result"
            with patch.object(planner.time, "monotonic", side_effect=[0, 1, 601, 602]):
                result, calls = self.run_planner(output)
            self.assertEqual(result, 1)
            self.assertEqual([lane for lane, _ in calls], ["parallel"])
            self.assertFalse((output / "manifest.json").exists())


class RunnerTests(unittest.TestCase):
    def test_native_plan_controls_only_selected_files_and_preserves_real_lane(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "manifest.json"
            target.write_text(
                json.dumps(manifest.make_plan(lanes(), 1, inputs())), encoding="utf-8"
            )
            digest = hashlib.sha256(target.read_bytes()).hexdigest()

            def execute(command, **kwargs):
                discovery = Path(command[-1][1:]).read_text().splitlines()
                self.assertEqual(
                    discovery, ["tests", "--ignore=tests/test_b.py", "--ignore=tests/test_pure.py"]
                )
                self.assertIn("scripts.pytest_native_selection", command)
                self.assertIn(f"--native-plan-sha256={digest}", command)
                self.assertIn("--max-worker-restart=0", command)
                self.assertIn(manifest.EXPRESSIONS["parallel"], command)
                self.assertIn("--template-postgres", command)
                self.assertIn("--cov-fail-under=0", command)
                self.assertEqual(command[command.index("-n") + 1], "auto")
                self.assertTrue(kwargs["env"]["COVERAGE_FILE"].endswith("-parallel"))
                return SimpleNamespace(returncode=0)

            with (
                patch.object(runner, "require_identity"),
                patch.object(
                    runner, "load_durations", side_effect=AssertionError("SQLite weights consulted")
                ),
                patch.object(
                    runner,
                    "test_files",
                    return_value=["tests/test_a.py", "tests/test_b.py", "tests/test_pure.py"],
                ),
                patch.object(runner.subprocess, "run", side_effect=execute),
            ):
                self.assertEqual(
                    runner.main(
                        [
                            "0",
                            "1",
                            "--postgres-mode",
                            "parallel",
                            "--workers",
                            "auto",
                            "--template-postgres",
                            "--native-plan",
                            str(target),
                            "--native-plan-sha256",
                            digest,
                        ]
                    ),
                    0,
                )

    def test_missing_stale_or_corrupt_plan_never_starts_pytest_or_falls_back(self):
        for error in (FileNotFoundError(), ValueError("stale source")):
            with (
                patch.object(runner, "read_plan", side_effect=error),
                patch.object(runner.subprocess, "run") as run,
                patch.object(runner, "select_shard") as fallback,
                self.assertRaises(SystemExit),
            ):
                runner.main(
                    [
                        "0",
                        "4",
                        "--postgres-mode",
                        "parallel",
                        "--native-plan",
                        "missing",
                        "--native-plan-sha256",
                        "a" * 64,
                    ]
                )
            run.assert_not_called()
            fallback.assert_not_called()


class RealGuardTests(unittest.TestCase):
    @unittest.skipUnless(
        importlib.util.find_spec("pytest") and importlib.util.find_spec("xdist"),
        "Requires the existing backend test runtime, no packages are installed by this test",
    )
    def test_real_workers_refuse_before_fixture_setup(self):
        repository = Path(__file__).resolve().parents[2]
        git = shutil.which("git") or self.fail("Git is required for the temporary checkout")
        with tempfile.TemporaryDirectory(prefix="ase-native-guard-") as temporary:
            work = Path(temporary)
            evidence = Path(os.environ.get("ASE_NATIVE_GUARD_EVIDENCE", work / "evidence"))
            evidence.mkdir(parents=True, exist_ok=False)
            root = work / "checkout"
            records = []

            def execute(label, command, cwd, environment=None):
                # Fixed local Git/pytest commands, no shell or application imports.
                with (evidence / f"{label}.log").open("xb") as output:
                    result = subprocess.run(  # noqa: S603
                        command,
                        cwd=cwd,
                        env=environment,
                        stdout=output,
                        stderr=subprocess.STDOUT,
                        check=False,
                        timeout=60,
                    )
                records.append({"label": label, "command": command, "exit": result.returncode})
                (evidence / "commands.json").write_text(
                    json.dumps(records, indent=2), encoding="utf-8"
                )
                return result.returncode

            clone = [git, "clone", "--shared", "--no-checkout", str(repository), str(root)]
            self.assertEqual(execute("clone", clone, work), 0)
            self.assertEqual(execute("empty-index", [git, "read-tree", "--empty"], root), 0)
            scripts = root / "scripts"
            tests = root / "backend/tests"
            scripts.mkdir()
            tests.mkdir(parents=True)
            for name in ("native_shard_manifest.py", "pytest_native_selection.py"):
                shutil.copyfile(repository / "scripts" / name, scripts / name)
            (tests / "conftest.py").write_text(
                """import os
from pathlib import Path
import pytest

def pytest_addoption(parser):
    for name in ("isolated-postgres", "owned-migrations", "template-postgres"):
        parser.addoption("--" + name, action="store_true")

def pytest_collection_modifyitems(config, items):
    if getattr(config, "workerinput", {}).get("workerid") != "gw1":
        return
    mode = os.environ["GUARD_CASE"]
    if mode == "missing":
        items.pop()
    elif mode == "extra":
        items[0]._nodeid += "[unexpected]"
    elif mode == "duplicate":
        items.append(items[0])

@pytest.fixture(autouse=True)
def sentinel():
    with Path(os.environ["GUARD_SENTINEL"]).open("a") as stream:
        stream.write("fixture reached\\n")
""",
                encoding="utf-8",
            )
            case = "import pytest, sys\n@pytest.mark.db\ndef test_ok():\n"
            case += "    assert 'ase' not in sys.modules\n"
            for name in ("test_one.py", "test_two.py"):
                (tests / name).write_text(case, encoding="utf-8")
            ids = [f"tests/{name}::test_ok" for name in ("test_one.py", "test_two.py")]
            plan = manifest.make_plan(
                {"parallel": ids, "serial": ["tests/test_race.py::test_race"]},
                1,
                manifest.identity(root),
            )
            target = evidence / "manifest.json"
            target.write_text(json.dumps(plan), encoding="utf-8")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            environment = {
                name: value
                for name, value in os.environ.items()
                if name in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE"}
            }
            environment.update(
                PYTHONPATH=str(root),
                PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                PYTHONDONTWRITEBYTECODE="1",
            )
            for mode in ("accepted", "digest", "source", "missing", "extra", "duplicate"):
                sentinel = evidence / f"{mode}-fixture.txt"
                environment.update(GUARD_CASE=mode, GUARD_SENTINEL=str(sentinel))
                changed = tests / "test_one.py"
                if mode == "source":
                    changed.write_text(case + "# source changed after planning\n", encoding="utf-8")
                command = [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    "-p",
                    "xdist.plugin",
                    "-p",
                    "scripts.pytest_native_selection",
                    f"--rootdir={root / 'backend'}",
                    "-n",
                    "2",
                    "--max-worker-restart=0",
                    "-o",
                    "markers=db: synthetic native selection",
                    "-m",
                    manifest.EXPRESSIONS["parallel"],
                    "--isolated-postgres",
                    "--owned-migrations",
                    "--template-postgres",
                    f"--native-plan={target}",
                    f"--native-plan-sha256={'0' * 64 if mode == 'digest' else digest}",
                    "--native-lane=parallel",
                    "--native-shard=0",
                    "--native-shards=1",
                    "tests",
                ]
                try:
                    code = execute(mode, command, root / "backend", environment)
                    self.assertEqual(code == 0, mode == "accepted", mode)
                    self.assertEqual(sentinel.exists(), mode == "accepted", mode)
                finally:
                    changed.write_text(case, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
