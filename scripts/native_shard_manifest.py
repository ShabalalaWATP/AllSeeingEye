"""Source-bound, selection-first PostgreSQL shard plans, never test classification."""

from __future__ import annotations

import hashlib
import heapq
import importlib.metadata
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

EXPRESSIONS = {
    "parallel": "(db and not (postgres or migration or race)) or owned_migration",
    "serial": "(postgres or migration or race) and not owned_migration",
}
VERSION = 1


def _git(root: Path, *arguments: str) -> bytes:
    executable = shutil.which("git")
    if executable is None:
        raise ValueError("Git is required to verify native source inputs")
    return subprocess.run(  # noqa: S603 - fixed Git executable and read-only arguments.
        [executable, *arguments], cwd=root, check=True, capture_output=True, timeout=30
    ).stdout


def source_identity(root: Path) -> dict[str, Any]:
    """Witness actual input bytes, including new test sources in a dirty prototype.

    Checkpoints detect input drift; they do not defend against an adversary changing
    and restoring files between reads. Concurrent checkout writes remain prohibited.
    Runtime outputs belong outside the checkout or in its existing ignored paths.
    """
    root = root.resolve()
    arguments = (
        "ls-files",
        "-z",
        "--cached",
        "--",
        "backend",
        "scripts",
        ".github/workflows/ci.yml",
    )
    extra_arguments = (
        "ls-files",
        "-z",
        "--others",
        "--exclude-standard",
        "--",
        ":(glob)backend/**/*.py",
        ":(glob)scripts/**/*.py",
    )
    listed = _git(root, *arguments)
    extra = _git(root, *extra_arguments)
    names = set((listed + extra).decode("utf-8").split("\0")) - {""}
    # Ignored Python tests/helpers must not evade the source witness.
    names.update(
        path.relative_to(root).as_posix()
        for path in (root / "backend/tests").rglob("*.py")
        if "__pycache__" not in path.parts
    )
    files = {}
    for name in sorted(names):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError("Native source inputs must be ordinary files inside the checkout")
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if listed != _git(root, *arguments) or extra != _git(root, *extra_arguments):
        raise ValueError("Native source inventory changed while being read")
    return {"head": _git(root, "rev-parse", "HEAD").decode().strip(), "files": files}


def runtime_identity() -> dict[str, Any]:
    packages = sorted(
        (re.sub(r"[-_.]+", "-", distribution.metadata["Name"]).lower(), distribution.version)
        for distribution in importlib.metadata.distributions()
    )
    if len({name for name, _version in packages}) != len(packages):
        raise ValueError("Native runtime contains ambiguous distribution identities")
    return {
        "implementation": platform.python_implementation(),
        "python": sys.version,
        "executable_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        "packages": [list(pair) for pair in packages],
    }


def identity(root: Path) -> dict[str, Any]:
    return {"source": source_identity(root), "runtime": runtime_identity()}


def node_file(nodeid: str) -> str:
    if not isinstance(nodeid, str) or any(character in nodeid for character in "\r\n\0"):
        raise ValueError("Invalid native node ID")
    filename, separator, test = nodeid.partition("::")
    path = PurePosixPath(filename)
    if (
        not separator
        or not test
        or not filename.startswith("tests/")
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in filename
        or ":" in filename
        or path.as_posix() != filename
        or path.suffix != ".py"
    ):
        raise ValueError("Native node IDs must name repository Python tests")
    return filename


def selected_ids(values: Any) -> list[str]:
    if not isinstance(values, list) or not values:
        raise ValueError("A native lane needs a non-empty node-ID list")
    for value in values:
        node_file(value)
    if len(values) != len(set(values)):
        raise ValueError("Duplicate native node ID")
    return sorted(values)


def partition(values: list[str], count: int) -> list[list[str]]:
    """Keep each selected file whole; positive case counts are scheduling weights."""
    if type(count) is not int or not 1 <= count <= 64:
        raise ValueError("Invalid native shard count")
    groups: dict[str, list[str]] = {}
    for nodeid in selected_ids(values):
        groups.setdefault(node_file(nodeid), []).append(nodeid)
    if len(groups) < count:
        raise ValueError("Native lane has fewer selected files than shards")
    queue = [(0, index) for index in range(count)]
    shards: list[list[str]] = [[] for _ in range(count)]
    for filename in sorted(groups, key=lambda name: (-len(groups[name]), name)):
        load, index = heapq.heappop(queue)
        shards[index].extend(groups[filename])
        heapq.heappush(queue, (load + len(groups[filename]), index))
    return [sorted(shard) for shard in shards]


def make_plan(lanes: dict[str, list[str]], count: int, inputs: dict[str, Any]) -> dict[str, Any]:
    if set(lanes) != set(EXPRESSIONS):
        raise ValueError("Both original native lanes are required")
    selected = {lane: selected_ids(values) for lane, values in lanes.items()}
    if set(selected["parallel"]) & set(selected["serial"]):
        raise ValueError("Native lanes must be disjoint")
    return {
        "version": VERSION,
        "identity": inputs,
        "count": count,
        "weight": "selected-case-count",
        "lanes": {
            lane: {
                "expression": EXPRESSIONS[lane],
                "ids": values,
                "shards": partition(values, count),
            }
            for lane, values in selected.items()
        },
    }


def validate_plan(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict) or set(document) != {
        "version",
        "identity",
        "count",
        "weight",
        "lanes",
    }:
        raise ValueError("Invalid native plan fields")
    if type(document["version"]) is not int or document["version"] != VERSION:
        raise ValueError("Unsupported native plan version")
    inputs = document["identity"]
    if not isinstance(inputs, dict) or set(inputs) != {"source", "runtime"}:
        raise ValueError("Native source and runtime witnesses are required")
    source = inputs["source"]
    if (
        not isinstance(source, dict)
        or set(source) != {"head", "files"}
        or not isinstance(source["head"], str)
        or re.fullmatch(r"[0-9a-f]{40}", source["head"]) is None
        or not isinstance(source["files"], dict)
        or not source["files"]
    ):
        raise ValueError("Invalid native source witness")
    for name, digest in source["files"].items():
        if (
            not isinstance(name, str)
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise ValueError("Invalid native source digest")
        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in name
            or ":" in name
            or path.as_posix() != name
            or not (name.startswith(("backend/", "scripts/")) or name == ".github/workflows/ci.yml")
        ):
            raise ValueError("Invalid native source path")
    runtime = inputs["runtime"]
    if (
        not isinstance(runtime, dict)
        or set(runtime) != {"implementation", "python", "executable_sha256", "packages"}
        or not all(
            isinstance(runtime[key], str) and runtime[key] for key in ("implementation", "python")
        )
        or not isinstance(runtime["packages"], list)
        or not runtime["packages"]
    ):
        raise ValueError("Invalid native runtime witness")
    if (
        not isinstance(runtime["executable_sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", runtime["executable_sha256"]) is None
    ):
        raise ValueError("Invalid native interpreter witness")
    if any(
        not isinstance(pair, list)
        or len(pair) != 2
        or not all(isinstance(value, str) and value for value in pair)
        for pair in runtime["packages"]
    ):
        raise ValueError("Invalid native package witness")
    if len({pair[0] for pair in runtime["packages"]}) != len(runtime["packages"]):
        raise ValueError("Duplicate native package witness")
    lanes = document["lanes"]
    if not isinstance(lanes, dict) or set(lanes) != set(EXPRESSIONS):
        raise ValueError("Invalid native lanes")
    for record in lanes.values():
        if not isinstance(record, dict) or set(record) != {"expression", "ids", "shards"}:
            raise ValueError("Invalid native lane fields")
    expected = make_plan(
        {lane: record["ids"] for lane, record in lanes.items()}, document["count"], inputs
    )
    if expected != document:
        raise ValueError("Native plan is not the complete deterministic partition")
    return document


def read_plan(path: Path, expected_sha256: str) -> dict[str, Any]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Native plan differs from its upstream digest")

    def unique_pairs(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate native plan JSON field")
            value[key] = item
        return value

    return validate_plan(json.loads(raw, object_pairs_hook=unique_pairs))


def planned_ids(plan: dict[str, Any], lane: str, index: int, count: int) -> list[str]:
    validate_plan(plan)
    if (
        lane not in EXPRESSIONS
        or type(index) is not int
        or not 0 <= index < count
        or count != plan["count"]
    ):
        raise ValueError("Native shard does not match its plan")
    return plan["lanes"][lane]["shards"][index]


def require_identity(plan: dict[str, Any], root: Path) -> None:
    if identity(root) != plan["identity"]:
        raise ValueError("Native source or installed runtime differs from its plan")


def require_ids(expected: list[str], actual: list[str]) -> None:
    if selected_ids(actual) != expected:
        raise ValueError("Native collection differs from its planned selected IDs")
