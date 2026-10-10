"""Fail when handwritten code or CSS exceeds 400 lines; warn above 350.

Usage: python scripts/check_file_length.py
Scope and reviewed target exceptions: docs/MAINTAINABILITY.md.
"""

from __future__ import annotations

import sys
from os import walk
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = (
    ROOT / "backend" / "src",
    ROOT / "backend" / "tests",
    ROOT / "frontend" / "src",
    ROOT / "frontend" / "scripts",
    ROOT / "scripts",
)
SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".css"}
GENERATED_SUFFIXES = (".gen.ts", ".d.ts")
EXCLUDED = {ROOT / "frontend" / "src" / "components" / "brand" / "EvilEyeSurface.tsx"}
EXCLUDED_DIRS = {"node_modules", ".venv", "__pycache__"}
WARN_AT = 350
FAIL_AT = 400


def line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def candidate_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCAN_DIRS:
        for current, directories, names in walk(directory):
            directories[:] = [name for name in directories if name not in EXCLUDED_DIRS]
            files.extend(Path(current) / name for name in names)
    # Tool configuration is executable code too. Do not descend into installed
    # dependencies or build output beside these top-level frontend files.
    files.extend((ROOT / "frontend").glob("*"))
    return [
        path
        for path in files
        if path.suffix in SUFFIXES
        and not path.name.endswith(GENERATED_SUFFIXES)
        and path not in EXCLUDED
        and path.is_file()
    ]


def main() -> int:
    failures = 0
    for path in sorted(candidate_files()):
        lines = line_count(path)
        relative = path.relative_to(ROOT)
        if lines > FAIL_AT:
            print(f"FAIL {relative}: {lines} lines (limit {FAIL_AT})")
            failures += 1
        elif lines > WARN_AT:
            print(f"WARN {relative}: {lines} lines (target {WARN_AT})")
    if failures:
        print(
            f"{failures} file(s) exceed {FAIL_AT} lines. Split them by responsibility."
        )
        return 1
    print("File length check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
