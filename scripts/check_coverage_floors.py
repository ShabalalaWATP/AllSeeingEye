"""Check reviewed security floors or frontend branch headroom in coverage JSON.

Backend input comes from ``coverage json`` after combining every SQLite shard.
Frontend input is Vitest's ``coverage-summary.json`` after merging every blob.
Use --report-only to measure the remaining test work before enabling a new gate;
invalid/incomplete input still fails. Existing global CI gates remain separate.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

BACKEND_SECURITY = (
    "application/auth/*.py",
    "*/authorisation.py",
    "domain/access.py",
    "adapters/persistence/tokens.py",
    "adapters/persistence/token_families.py",
    "adapters/persistence/session.py",
    "domain/grading.py",
    "*validation*.py",
)
FRONTEND_AUTH = ("features/auth/*", "stores/auth.ts")
SECURITY_FLOOR = 95


def percentage(covered: object, total: object) -> float:
    if type(covered) is not int or type(total) is not int or not 0 <= covered <= total:
        raise ValueError("Coverage counts must be non-negative integers with covered <= total")
    return 100 * covered / total if total else 100.0


def relative_path(name: str, prefix: str) -> str:
    normal = name.replace("\\", "/")
    marker = f"/{prefix}/"
    if marker in normal:
        return normal.split(marker, 1)[1]
    if normal.startswith(prefix + "/"):
        return normal[len(prefix) + 1 :]
    raise ValueError(f"Coverage path is outside {prefix}: {normal}")


def backend_failures(document: dict) -> list[str]:
    files = document["files"]
    if not files:
        raise ValueError("Backend coverage has no files")
    failures = []
    matched = set()
    for name, data in sorted(files.items()):
        relative = relative_path(name, "src/ase")
        patterns = {
            pattern for pattern in BACKEND_SECURITY if fnmatch.fnmatchcase(relative, pattern)
        }
        if not patterns:
            continue
        matched.update(patterns)
        summary = data["summary"]
        for metric, covered, total in (
            ("lines", "covered_lines", "num_statements"),
            ("branches", "covered_branches", "num_branches"),
        ):
            value = percentage(summary[covered], summary[total])
            if value < SECURITY_FLOOR:
                failures.append(f"{relative}: {metric} {value:.2f}% < {SECURITY_FLOOR}%")
    missing = set(BACKEND_SECURITY) - matched
    if missing:
        raise ValueError(f"Security coverage patterns have no files: {', '.join(sorted(missing))}")
    return failures


def frontend_failures(document: dict, *, auth: bool = False) -> list[str]:
    total = document["total"]["branches"]
    global_branches = percentage(total["covered"], total["total"])
    failures = []
    if not auth and global_branches < 92:
        failures.append(f"frontend total: branches {global_branches:.2f}% < 92%")
    files = [(name, data) for name, data in document.items() if name != "total"]
    if not files:
        raise ValueError("Frontend coverage has no files")
    matched = set()
    worst = []
    for name, data in files:
        relative = relative_path(name, "src")
        branch = data["branches"]
        value = percentage(branch["covered"], branch["total"])
        if branch["total"] >= 20:
            worst.append((value, relative, branch["total"] - branch["covered"]))
            if not auth and value < 70:
                failures.append(
                    f"{relative}: branches {value:.2f}% < 70% ({branch['total']} branches)"
                )
        patterns = {pattern for pattern in FRONTEND_AUTH if fnmatch.fnmatchcase(relative, pattern)}
        if auth and patterns:
            matched.update(patterns)
            for metric in ("lines", "branches"):
                summary = data[metric]
                value = percentage(summary["covered"], summary["total"])
                if value < SECURITY_FLOOR:
                    failures.append(f"{relative}: {metric} {value:.2f}% < {SECURITY_FLOOR}%")
    if auth and set(FRONTEND_AUTH) != matched:
        raise ValueError("Frontend authentication coverage is incomplete")
    if not auth:
        print("Lowest frontend branch coverage (at least 20 branches):")
        for value, relative, missing in sorted(worst)[:10]:
            print(f"  {value:6.2f}% {relative} ({missing} uncovered)")
    return sorted(failures)


def expected_modules(policy: str) -> set[str]:
    root = Path(__file__).resolve().parents[1]
    source = root / ("backend/src/ase" if policy == "backend-security" else "frontend/src")
    patterns = BACKEND_SECURITY if policy == "backend-security" else FRONTEND_AUTH
    if policy == "frontend-branches":
        return set()
    return {
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file()
        and path.suffix in {".py", ".ts", ".tsx"}
        and ".test." not in path.name
        and any(
            fnmatch.fnmatchcase(path.relative_to(source).as_posix(), pattern)
            for pattern in patterns
        )
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--policy",
        choices=("backend-security", "frontend-auth", "frontend-branches"),
        required=True,
    )
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.report.read_text(encoding="utf-8"))
        backend = args.policy == "backend-security"
        names = (
            document["files"]
            if backend
            else {name: data for name, data in document.items() if name != "total"}
        )
        present = {relative_path(name, "src/ase" if backend else "src") for name in names}
        missing = expected_modules(args.policy) - present
        if missing:
            raise ValueError(f"Missing reviewed modules: {', '.join(sorted(missing))}")
        failures = (
            backend_failures(document)
            if args.policy == "backend-security"
            else frontend_failures(document, auth=args.policy == "frontend-auth")
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Invalid coverage report: {error}", file=sys.stderr)
        return 2
    for failure in failures:
        print(f"{'GAP' if args.report_only else 'FAIL'} {failure}")
    if not failures:
        print(f"Coverage floors passed: {args.policy}")
    return 1 if failures and not args.report_only else 0


if __name__ == "__main__":
    sys.exit(main())
