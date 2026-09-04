"""Fail when a hand-written source file exceeds 400 lines; warn above 350.

Usage: python scripts/check_file_length.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = (
    ROOT / "backend" / "src",
    ROOT / "backend" / "tests",
    ROOT / "frontend" / "src",
)
SUFFIXES = {".py", ".ts", ".tsx"}
GENERATED_SUFFIXES = (".gen.ts", ".d.ts")
EXCLUDED = {ROOT / "frontend" / "src" / "components" / "brand" / "EvilEye.tsx"}
WARN_AT = 350
FAIL_AT = 400


def line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def candidate_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCAN_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.suffix not in SUFFIXES or path.name.endswith(GENERATED_SUFFIXES):
                continue
            if path in EXCLUDED or "node_modules" in path.parts:
                continue
            files.append(path)
    return files


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
        print(f"{failures} file(s) exceed {FAIL_AT} lines. Split them by responsibility.")
        return 1
    print("File length check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
