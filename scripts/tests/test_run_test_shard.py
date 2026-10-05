"""Regression checks for complete, isolated CI shard execution."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_test_shard as runner


class ShardTests(unittest.TestCase):
    def test_complete_disjoint_balanced_and_deterministic(self):
        files = [f"tests/test_{number:04}.py" for number in range(103)]
        shards = [runner.select_shard(list(reversed(files)), index, 8) for index in range(8)]
        flattened = [filename for shard in shards for filename in shard]
        self.assertEqual(sorted(flattened), files)
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertLessEqual(max(map(len, shards)) - min(map(len, shards)), 1)
        for index, shard in enumerate(shards):
            self.assertEqual(shard, runner.select_shard(files, index, 8))

    def test_invalid_bounds(self):
        for index, count in [(-1, 8), (8, 8), (0, 0), (0, -1)]:
            with self.subTest(index=index, count=count), self.assertRaises(ValueError):
                runner.select_shard(["tests/test_example.py"], index, count)

    def test_discovery_includes_both_pytest_patterns_and_nested_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = Path(directory)
            for name in ["test_a.py", "nested/test_b.py", "nested/c_test.py", "helper.py"]:
                target = backend / "tests" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch()
            self.assertEqual(
                runner.test_files(backend),
                ["tests/nested/c_test.py", "tests/nested/test_b.py", "tests/test_a.py"],
            )

    def test_subprocess_propagates_failure_and_preserves_database_environment(self):
        argument_files = []

        def fail(command, **_kwargs):
            arguments = Path(command[-1].removeprefix("@"))
            argument_files.append(arguments)
            self.assertEqual(arguments.read_text(encoding="utf-8"), "tests\n")
            return SimpleNamespace(returncode=1)

        with (
            patch.object(runner, "test_files", return_value=["tests/test_a.py"]),
            patch.dict(runner.os.environ, {"ASE_TEST_DATABASE_URL": "test-database"}),
            patch.object(runner.subprocess, "run", side_effect=fail) as run,
        ):
            self.assertEqual(runner.main(["0", "1"]), 1)
            args, kwargs = run.call_args
            self.assertIn("--cov-fail-under=0", args[0])
            self.assertIn("--durations=20", args[0])
            self.assertFalse(any(value.startswith("--record-test-phases=") for value in args[0]))
            self.assertTrue(args[0][-1].startswith("@"))
            self.assertFalse(argument_files[0].exists())
            self.assertEqual(kwargs["env"]["ASE_TEST_DATABASE_URL"], "test-database")
            self.assertEqual(
                kwargs["env"]["COVERAGE_FILE"], str(runner.BACKEND / ".coverage.shard-0")
            )

    def test_single_root_discovery_excludes_exactly_other_partition_files(self):
        files = ["tests/test_a.py", "tests/nested/test_b.py", "tests/nested/c_test.py"]
        for index in range(2):
            selected = runner.select_shard(files, index, 2)
            arguments = runner.collection_arguments(files, selected)
            self.assertEqual(arguments[0], "tests")
            excluded = {argument.removeprefix("--ignore=") for argument in arguments[1:]}
            self.assertEqual(set(files) - excluded, set(selected))
        with self.assertRaisesRegex(ValueError, "line separators"):
            runner.collection_arguments(["tests/test_a\n--pdb.py"], [])

    def test_recorded_durations_balance_complete_files_deterministically(self):
        durations = {f"tests/test_{number:03}.py": float(number % 17) for number in range(90)}
        durations["tests/test_slow.py"] = 40.0
        files = [*durations, "tests/test_new.py"]
        shards = [
            runner.select_shard(list(reversed(files)), index, 4, durations) for index in range(4)
        ]
        flattened = [name for shard in shards for name in shard]
        self.assertEqual(sorted(flattened), sorted(files))
        self.assertEqual(len(flattened), len(set(flattened)))
        median = 8.0  # Unrecorded files count as the median recorded file.
        loads = [sum(durations.get(name, median) for name in shard) for shard in shards]
        # Longest-first placement leaves shards within one short file of each other.
        self.assertLess(max(loads) - min(loads), 17.0)
        for index, shard in enumerate(shards):
            self.assertEqual(shard, sorted(shard))
            self.assertEqual(shard, runner.select_shard(files, index, 4, dict(durations)))

    def test_durations_beat_round_robin_when_one_file_dominates(self):
        files = [f"tests/test_{number:02}.py" for number in range(16)]
        durations = dict.fromkeys(files, 1.0) | {files[0]: 12.0, files[4]: 12.0}
        balanced = [runner.select_shard(files, index, 4, durations) for index in range(4)]
        robin = [runner.select_shard(files, index, 4) for index in range(4)]

        def slowest(shards):
            return max(sum(durations[name] for name in shard) for shard in shards)

        self.assertEqual(slowest(robin), 26.0)
        self.assertEqual(slowest(balanced), 12.0)

    def test_missing_durations_fall_back_to_round_robin(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(runner.load_durations(Path(directory) / "absent.json"), {})
        files = ["tests/test_a.py", "tests/test_b.py", "tests/test_c.py"]
        self.assertEqual(
            runner.select_shard(files, 0, 2, {}), ["tests/test_a.py", "tests/test_c.py"]
        )

    def test_invalid_durations_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "durations.json"
            for content in ["[]", '{"tests/test_a.py": -1}', '{"tests/test_a.py": true}', "{"]:
                target.write_text(content, encoding="utf-8")
                with self.subTest(content=content), self.assertRaises(ValueError):
                    runner.load_durations(target)
            with (
                patch.object(runner, "DURATIONS", target),
                patch.object(runner.subprocess, "run") as run,
                self.assertRaises(SystemExit) as error,
            ):
                runner.main(["0", "1"])
            self.assertEqual(error.exception.code, 2)
            run.assert_not_called()

    def test_workers_are_validated_and_passed_to_pytest(self):
        with (
            patch.object(runner, "test_files", return_value=["tests/test_a.py"]),
            patch.object(runner.subprocess, "run") as run,
        ):
            run.return_value.returncode = 0
            self.assertEqual(runner.main(["0", "1", "--workers", "auto"]), 0)
            self.assertEqual(run.call_args[0][0][-3:-1], ["-n", "auto"])
            self.assertTrue(run.call_args[0][0][-1].startswith("@"))
            self.assertEqual(runner.main(["0", "1"]), 0)
            self.assertNotIn("-n", run.call_args[0][0])
            for invalid in ["0", "-1", "all", "2 --pdb"]:
                with self.subTest(workers=invalid), self.assertRaises(SystemExit):
                    runner.main(["0", "1", "--workers", invalid])

    def test_committed_durations_are_valid(self):
        recorded = runner.load_durations(runner.DURATIONS)
        self.assertTrue(all(name.startswith("tests/test_") for name in recorded))

    def test_postgres_parallel_and_serial_phases_are_disjoint(self):
        with (
            patch.object(runner, "test_files", return_value=["tests/test_a.py"]),
            patch.object(runner.subprocess, "run") as run,
        ):
            run.return_value.returncode = 0
            runner.main(["0", "1", "--postgres-mode", "parallel", "--workers", "2"])
            parallel = run.call_args[0][0]
            self.assertIn(
                "(db and not (postgres or migration or race)) or owned_migration", parallel
            )
            self.assertIn("--isolated-postgres", parallel)
            self.assertIn("--durations=0", parallel)
            self.assertIn("--durations-min=0", parallel)
            self.assertIn(
                "--record-test-phases=.test-phases.postgres-0-parallel.controller.jsonl", parallel
            )
            self.assertTrue(run.call_args[1]["env"]["COVERAGE_FILE"].endswith("-parallel"))
            runner.main(["0", "1", "--postgres-mode", "serial"])
            serial = run.call_args[0][0]
            self.assertIn("(postgres or migration or race) and not owned_migration", serial)
            self.assertNotIn("-n", serial)
            self.assertIn("--durations=0", serial)
            self.assertIn("--durations-min=0", serial)
            self.assertIn(
                "--record-test-phases=.test-phases.postgres-0-serial.controller.jsonl", serial
            )
            self.assertTrue(run.call_args[1]["env"]["COVERAGE_FILE"].endswith("-serial"))
            with self.assertRaises(SystemExit):
                runner.main(["0", "1", "--postgres-mode", "serial", "--workers", "2"])

    def test_empty_shard_does_not_accidentally_run_the_full_suite(self):
        with (
            patch.object(runner, "test_files", return_value=[]),
            patch.object(runner.subprocess, "run") as run,
            self.assertRaises(SystemExit) as error,
        ):
            runner.main(["0", "8"])
        self.assertEqual(error.exception.code, 2)
        run.assert_not_called()

    def test_template_fixture_opt_in_is_limited_to_parallel_postgres(self):
        with (
            patch.object(runner, "test_files", return_value=["tests/test_a.py"]),
            patch.object(runner.subprocess, "run") as run,
        ):
            run.return_value.returncode = 0
            self.assertEqual(
                runner.main(["0", "1", "--postgres-mode", "parallel", "--template-postgres"]),
                0,
            )
            self.assertIn("--template-postgres", run.call_args[0][0])
            self.assertIn("--isolated-postgres", run.call_args[0][0])
            runner.main(["0", "1", "--postgres-mode", "parallel"])
            self.assertNotIn("--template-postgres", run.call_args[0][0])
            run.reset_mock()
            for mode in [[], ["--postgres-mode", "serial"]]:
                with self.subTest(mode=mode), self.assertRaises(SystemExit) as error:
                    runner.main(["0", "1", *mode, "--template-postgres"])
                self.assertEqual(error.exception.code, 2)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
