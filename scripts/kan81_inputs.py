"""Source and dependency witnesses for the single KAN-81 Linux observation."""

import hashlib
import json
import platform
import subprocess
from pathlib import Path

BASELINE = "88164eb99150d5d94367f8257569100684f9e619"
CANDIDATE = "38c487c93c79464dd0bbd9ed00c491b779a9a437"
CANDIDATE_FRONTEND_TREE = "b1f2e5940f5490cabff8dde1a62aeebe4e016507"
CANDIDATE_PINS = {
    "src/features/globe/conflictScope.ts": "9709b9a4ec114b99165d6c13e8861ba77208caa2bd1ce116fa338c5e5834987f",
    "src/features/globe/useConflictFilters.ts": "ed754e4ff6d0f07ac121c39bf1771d1154683f13c68144c0316696cfc86434fd",
    "src/features/globe/conflictScope-equivalence.test.tsx": "387d8bd8b58c6354db926d376b16a492989bd5a7e2ec340fbcbfd33e031f5a44",
    "src/features/globe/conflictScope-budget.test.tsx": "bf1844433adc5e14309f693c94d9104d6964c23bc765d83f1722d53f9074fccc",
}
BENCHMARK = "src/features/globe/GlobePage.streamBenchmark.test.tsx"
OVERLAY = ("package.json", "pnpm-lock.yaml")
PINS = {
    "package.json": "e9a8f2d5399dcbbdaf2b7592b12100707881907fb1d0be690998292896a8799e",
    "pnpm-lock.yaml": "2b342e95ef4e3eded5d6f9a2890102e6249181b8f1d4c356800f625886c38127",
    ".npmrc": "b768bf74cd763563e6c6295f9ad1169da7885b372e80c8dd607da2c098e992dc",
    "vitest.config.ts": "da2e4e22c29437c97ea8009f9abc82a67f5590476765400aac22845a7da04b39",
    BENCHMARK: "55b6fd786cbcc10998a801adcc0626c108b483eb9a9b8d351e6a8e2ce2bdc254",
    "src/test/streamFixture.ts": "42fee34436e2a0a4d98d20ba85af9ca16ab5c7ae41bac9ad4f0b676b8e509786",
}


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["/usr/bin/git", "-C", str(root), *args],
        timeout=30,
        text=True,
    ).strip()


def sources(root: Path) -> dict[str, str]:
    paths = git(root, "ls-files", "frontend").splitlines()
    if not paths:
        raise RuntimeError("Missing tracked frontend")
    return {path: sha(root / path) for path in paths}


def verify_pins(frontend: Path) -> None:
    if any(sha(frontend / name) != expected for name, expected in PINS.items()):
        raise RuntimeError("Protected frontend inputs differ")


def verify_candidate(root: Path) -> dict:
    tree = git(root, "rev-parse", "HEAD:frontend")
    if tree != CANDIDATE_FRONTEND_TREE:
        raise RuntimeError("Candidate frontend tree differs")
    actual = {name: sha(root / "frontend" / name) for name in CANDIDATE_PINS}
    if actual != CANDIDATE_PINS:
        raise RuntimeError("Candidate conflict derivation differs")
    return {"revision": CANDIDATE, "frontendTree": tree, "files": actual}


def prepare_sources(baseline: Path, candidate: Path) -> dict:
    for root, revision in ((baseline, BASELINE), (candidate, CANDIDATE)):
        if git(root, "rev-parse", "HEAD") != revision or git(
            root, "status", "--porcelain"
        ):
            raise RuntimeError("Expected fresh immutable checkout")
        if (root / "frontend/node_modules").exists():
            raise RuntimeError("Dependency installation must be fresh")
    verify_pins(candidate / "frontend")
    candidate_identity = verify_candidate(candidate)
    original = sources(baseline)
    # Deliberate and recorded dependency normalisation, never a source backport.
    for name in OVERLAY:
        (baseline / "frontend" / name).write_bytes(
            (candidate / "frontend" / name).read_bytes()
        )
    verify_pins(baseline / "frontend")
    return {
        "baselineOriginal": original,
        "baseline": sources(baseline),
        "candidate": sources(candidate),
        "candidateIdentity": candidate_identity,
        "overlay": list(OVERLAY),
    }


def installed(frontend: Path) -> dict:
    packages = frontend / "node_modules/.pnpm"
    rows = {}
    manifests = list(packages.glob("*/node_modules/*/package.json"))
    manifests.extend(packages.glob("*/node_modules/@*/*/package.json"))
    for path in sorted(manifests):
        if path.parent.is_symlink():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        rows[path.relative_to(packages).as_posix()] = {
            "name": data.get("name"),
            "version": data.get("version"),
            "sha256": sha(path),
        }
    if not rows:
        raise RuntimeError("Missing installed dependency inventory")
    return {"packages": rows, "resolutionLock": sha(packages / "lock.yaml")}


def host() -> dict:
    cpu = [
        line
        for line in Path("/proc/cpuinfo").read_text().splitlines()
        if line.startswith(("model name", "cpu cores"))
    ]
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": cpu,
        "memory": Path("/proc/meminfo").read_text().splitlines()[:3],
    }
