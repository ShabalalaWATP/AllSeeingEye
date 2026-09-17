"""Regression checks for complete, isolated CI shard execution."""

import sys
import tempfile
import unittest
from pathlib import Path
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
        with (
            patch.object(runner, "test_files", return_value=["tests/test_a.py"]),
            patch.dict(runner.os.environ, {"ASE_TEST_DATABASE_URL": "test-database"}),
            patch.object(runner.subprocess, "run") as run,
        ):
            run.return_value.returncode = 1
            self.assertEqual(runner.main(["0", "1"]), 1)
            args, kwargs = run.call_args
            self.assertIn("--cov-fail-under=0", args[0])
            self.assertEqual(args[0][-1], "tests/test_a.py")
            self.assertEqual(kwargs["env"]["ASE_TEST_DATABASE_URL"], "test-database")
            self.assertEqual(
                kwargs["env"]["COVERAGE_FILE"], str(runner.BACKEND / ".coverage.shard-0")
            )

    def test_empty_shard_does_not_accidentally_run_the_full_suite(self):
        with (
            patch.object(runner, "test_files", return_value=[]),
            patch.object(runner.subprocess, "run") as run,
            self.assertRaises(SystemExit) as error,
        ):
            runner.main(["0", "8"])
        self.assertEqual(error.exception.code, 2)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
