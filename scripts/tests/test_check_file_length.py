"""Exercise the repository length gate against isolated handwritten files."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[1] / "check_file_length.py"


class FileLengthTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "scripts").mkdir()
        shutil.copyfile(CHECKER, self.root / "scripts" / CHECKER.name)

    def write(self, relative, lines, *, newline="\n"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((newline.join(["content"] * lines) + newline).encode())

    def check(self):
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / CHECKER.name)],
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_target_and_hard_limit_are_strictly_above_the_boundary(self):
        for lines, label, code in [
            (350, None, 0),
            (351, "WARN", 0),
            (400, "WARN", 0),
            (401, "FAIL", 1),
        ]:
            with self.subTest(lines=lines):
                self.write("backend/src/ase/example.py", lines)
                result = self.check()
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                if label is None:
                    self.assertNotIn("example.py", result.stdout)
                else:
                    self.assertIn(f"{label} backend", result.stdout)
                    self.assertIn(f"{lines} lines", result.stdout)

    def test_css_uses_the_same_hard_limit_as_application_code(self):
        self.write("frontend/src/features/reports/reader.css", 401)
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("reader.css: 401 lines (limit 400)", result.stdout)

    def test_repository_and_frontend_tooling_cannot_escape_the_gate(self):
        for relative in (
            "scripts/backup.py",
            "scripts/tests/test_backup.py",
            "frontend/scripts/bundle.js",
            "frontend/vite.config.ts",
            "frontend/eslint.config.js",
            "frontend/src/components/brand/EvilEye.tsx",
        ):
            with self.subTest(relative=relative):
                self.write(relative, 401)
                result = self.check()
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(Path(relative).name, result.stdout)
                (self.root / relative).unlink()

    def test_generated_declarations_vendor_source_and_dependencies_are_excluded(self):
        for relative in (
            "frontend/src/lib/api/types.gen.ts",
            "frontend/src/vite-env.d.ts",
            "frontend/src/components/brand/EvilEyeSurface.tsx",
            "frontend/node_modules/example/index.js",
            "frontend/scripts/node_modules/example/index.js",
            "scripts/.venv/example.py",
        ):
            self.write(relative, 401)
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("FAIL", result.stdout)

    def test_crlf_and_missing_final_newline_count_as_physical_lines(self):
        self.write("backend/tests/test_example.py", 400, newline="\r\n")
        path = self.root / "backend/tests/test_example.py"
        path.write_bytes(path.read_bytes().rstrip(b"\r\n"))
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("test_example.py: 400 lines", result.stdout)


if __name__ == "__main__":
    unittest.main()
