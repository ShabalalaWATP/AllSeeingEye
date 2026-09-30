"""Coverage gates reject missing branches, incomplete reports and low percentages."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_coverage_floors as checker


def frontend_data(covered=95, total=100):
    metrics = {"covered": covered, "total": total}
    return {"branches": metrics, "lines": metrics}


class CoverageFloorTests(unittest.TestCase):
    def test_deleted_authorisation_branch_fails_with_module_name(self):
        report = {
            "files": {
                "src/ase/application/reports/authorisation.py": {
                    "summary": {
                        "covered_lines": 100,
                        "num_statements": 100,
                        "covered_branches": 94,
                        "num_branches": 100,
                    }
                }
            }
        }
        with patch.object(checker, "BACKEND_SECURITY", ("*/authorisation.py",)):
            failures = checker.backend_failures(report)
        self.assertEqual(failures, ["application/reports/authorisation.py: branches 94.00% < 95%"])

    def test_empty_or_missing_security_files_fail(self):
        with self.assertRaises(ValueError):
            checker.backend_failures({"files": {}})
        with self.assertRaises(ValueError):
            checker.backend_failures({"files": {"src/ase/other.py": {}}})

    def test_floor_boundary_and_empty_modules_are_valid(self):
        self.assertEqual(checker.percentage(0, 0), 100)
        self.assertEqual(checker.percentage(95, 100), 95)
        for covered, total in [(101, 100), (-1, 2), (1, -1), (True, 1)]:
            with self.subTest(covered=covered), self.assertRaises(ValueError):
                checker.percentage(covered, total)

    def test_frontend_reports_global_and_large_file_regressions(self):
        report = {
            "total": frontend_data(91),
            "C:/repo/frontend/src/large.ts": frontend_data(13, 20),
            "C:/repo/frontend/src/small.ts": frontend_data(1, 2),
        }
        with contextlib.redirect_stdout(io.StringIO()) as output:
            failures = checker.frontend_failures(report)
        self.assertEqual(len(failures), 2)
        self.assertIn("large.ts", output.getvalue())
        self.assertNotIn("small.ts", output.getvalue())

    def test_auth_floors_apply_per_file(self):
        report = {
            "total": frontend_data(),
            "src/features/auth/Login.tsx": frontend_data(94),
            "src/stores/auth.ts": frontend_data(),
        }
        failures = checker.frontend_failures(report, auth=True)
        self.assertEqual(len(failures), 2)
        self.assertTrue(all("Login.tsx" in failure for failure in failures))

    def test_missing_reviewed_module_fails_even_in_diagnostic_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "coverage.json"
            report.write_text(json.dumps({"files": {"src/ase/domain/access.py": {}}}))
            expected = {"domain/access.py", "application/reports/authorisation.py"}
            for mode in ([], ["--report-only"]):
                with (
                    self.subTest(mode=mode),
                    patch.object(checker, "expected_modules", return_value=expected),
                    contextlib.redirect_stderr(io.StringIO()) as output,
                ):
                    result = checker.main([str(report), "--policy", "backend-security", *mode])
                self.assertEqual(result, 2)
                self.assertIn("application/reports/authorisation.py", output.getvalue())

    def test_windows_and_linux_paths_are_normalised(self):
        for path in [
            r"C:\repo\backend\src\ase\domain\access.py",
            "/repo/backend/src/ase/domain/access.py",
        ]:
            self.assertEqual(checker.relative_path(path, "src/ase"), "domain/access.py")
        with self.assertRaises(ValueError):
            checker.relative_path("private/unexpected.py", "src/ase")


if __name__ == "__main__":
    unittest.main()
