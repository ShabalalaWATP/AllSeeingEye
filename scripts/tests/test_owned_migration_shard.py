"""Owned migrations retain their coverage and census while joining private workers."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_test_shard as runner


class OwnedMigrationShardTests(unittest.TestCase):
    def test_parallel_admits_owned_cases_without_changing_worker_or_coverage_options(self):
        with (
            patch.object(runner, "test_files", return_value=["tests/test_example.py"]),
            patch.object(runner.subprocess, "run") as run,
        ):
            run.return_value.returncode = 0
            self.assertEqual(
                runner.main(["0", "1", "--postgres-mode", "parallel", "--workers", "4"]), 0
            )
            command = run.call_args.args[0]
            self.assertIn(
                "(db and not (postgres or migration or race)) or owned_migration", command
            )
            self.assertIn("--owned-migrations", command)
            self.assertIn("owned_postgres", command)
            self.assertIn("pythonpath=. tests", command)
            self.assertIn("--isolated-postgres", command)
            self.assertIn("--cov-fail-under=0", command)
            self.assertIn("--cov-report=", command)
            self.assertEqual(command[command.index("-n") + 1], "4")
            self.assertNotIn("ASE_NOTIFICATION_MIGRATION_POSTGRES_URL", run.call_args.kwargs["env"])

    def test_serial_retains_every_unadmitted_special_case(self):
        with (
            patch.object(runner, "test_files", return_value=["tests/test_example.py"]),
            patch.object(runner.subprocess, "run") as run,
        ):
            run.return_value.returncode = 0
            runner.main(["0", "1", "--postgres-mode", "serial"])
            command = run.call_args.args[0]
            self.assertIn("(postgres or migration or race) and not owned_migration", command)
            self.assertIn("owned_postgres", command)
            self.assertIn("pythonpath=. tests", command)
            self.assertNotIn("--owned-migrations", command)
            self.assertNotIn("-n", command)

    def test_default_sqlite_has_no_new_plugin_or_options(self):
        with (
            patch.object(runner, "test_files", return_value=["tests/test_example.py"]),
            patch.object(runner.subprocess, "run") as run,
        ):
            run.return_value.returncode = 0
            runner.main(["0", "1", "--workers", "4"])
            command = run.call_args.args[0]
            self.assertNotIn("owned_postgres", command)
            self.assertNotIn("--owned-migrations", command)
            self.assertNotIn("pythonpath=. tests", command)


if __name__ == "__main__":
    unittest.main()
