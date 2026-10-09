"""Prune old release records and image tags left by the VPS deployment controller.

Operator-run on the deployment host as the deployment account, never by the controller
or CI. A dry run is the default; --apply removes exactly what the dry run lists.
Standard library only. See docs/AUTOMATIC_DEPLOYMENT.md, "Pruning old releases".
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

# The installed controller's locations (scripts/deploy_vps.py STATE and ROOT).
STATE = Path("/home/ase/deployments")
CHECKOUT = Path("/home/ase/ase")
DEFAULT_KEEP = 5
MIN_KEEP = 2
TIMEOUT = 120
SHA = re.compile(r"[0-9a-f]{40}")
# deploy_vps.py names each record with tempfile.mkdtemp(prefix=f"{sha[:12]}-").
RECORD = re.compile(r"[0-9a-f]{12}-[a-z0-9_]{8}")
TAG = re.compile(r"(?:release|rollback)-([0-9a-f]{40})")
REPOSITORIES = frozenset({"ase-api", "ase-parser", "ase-web"})


class PruneError(RuntimeError):
    """Pruning was refused or an inventory step failed; nothing further is removed."""


@dataclass(frozen=True)
class Record:
    path: Path
    target: str
    previous: str
    created: float
    succeeded: bool
    has_worktree: bool


@dataclass(frozen=True)
class Tag:
    reference: str
    revision: str
    image: str


@dataclass(frozen=True)
class Plan:
    kept: list[Record]
    revisions: frozenset[str]
    records: list[Record]
    skipped: list[Record]
    tags: list[Tag]
    kept_tags: int


def run(*args: str) -> str:
    # Errors name the operation only, never subprocess output.
    try:
        result = subprocess.run(
            args, check=True, capture_output=True, text=True, timeout=TIMEOUT
        )
    except (subprocess.SubprocessError, OSError, UnicodeError) as exc:
        raise PruneError(
            f"Operation failed: {args[0]} {args[1] if len(args) > 1 else ''}"
        ) from exc
    return result.stdout.strip()


def operator_file(name: str) -> bool:
    """The lock and operator files beside the records are never candidates."""
    return name == "deployment.lock" or name.startswith(("manual-", "env-"))


def read_record(path: Path) -> Record | None:
    """A controller release record, or None for anything this script must leave alone."""
    if operator_file(path.name) or not RECORD.fullmatch(path.name):
        return None
    try:
        info = path.lstat()
        # Only a real directory: never a symbolic link, junction or file.
        if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_reparse_tag", 0):
            return None
        record_file = path / "release.json"
        if record_file.is_symlink():
            return None
        data = json.loads(record_file.read_text(encoding="utf-8"))
        created = record_file.stat().st_mtime
        succeeded = (path / "success").is_file()
        has_worktree = (path / "source").exists() or (path / "source").is_symlink()
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    target, previous = data.get("target"), data.get("previous")
    if not (isinstance(target, str) and SHA.fullmatch(target)):
        return None
    if not (isinstance(previous, str) and SHA.fullmatch(previous)):
        return None
    if not path.name.startswith(target[:12] + "-"):
        return None
    return Record(path, target, previous, created, succeeded, has_worktree)


def records(state: Path) -> list[Record]:
    """Release records, oldest first by the time each release.json was written."""
    found = [record for path in state.iterdir() if (record := read_record(path))]
    return sorted(found, key=lambda record: (record.created, record.path.name))


def release_tags() -> list[Tag]:
    listing = run(
        "docker",
        "image",
        "ls",
        "--no-trunc",
        "--format",
        "{{.Repository}}\t{{.Tag}}\t{{.ID}}",
    )
    found = []
    for line in listing.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        repository, tag, image = parts
        match = TAG.fullmatch(tag)
        if repository in REPOSITORIES and match:
            found.append(Tag(f"{repository}:{tag}", match[1], image))
    return found


def container_images() -> set[str]:
    """Images of every container, running or stopped; none of them is ever untagged."""
    containers = run("docker", "ps", "--all", "--quiet", "--no-trunc").split()
    if not containers:
        return set()
    return set(run("docker", "inspect", "--format", "{{.Image}}", *containers).split())


def head(checkout: Path) -> str:
    revision = run("git", "-C", str(checkout), "rev-parse", "HEAD")
    if not SHA.fullmatch(revision):
        raise PruneError("The checkout HEAD is not a full commit SHA.")
    return revision


def plan(
    found: list[Record], tags: list[Tag], in_use: set[str], current: str, keep: int
) -> Plan:
    if keep < MIN_KEEP:
        raise PruneError(f"Keep at least {MIN_KEEP} releases.")
    kept = found[-keep:]
    succeeded = [record for record in found if record.succeeded]
    if succeeded and succeeded[-1] not in kept:
        kept.insert(0, succeeded[-1])
    revisions = frozenset(
        {current}
        | {record.target for record in kept}
        | {record.previous for record in kept}
    )
    old = [record for record in found if record not in kept]
    doomed = [
        tag for tag in tags if tag.revision not in revisions and tag.image not in in_use
    ]
    return Plan(
        kept=kept,
        revisions=revisions,
        records=[record for record in old if not record.has_worktree],
        skipped=[record for record in old if record.has_worktree],
        tags=doomed,
        kept_tags=len(tags) - len(doomed),
    )


def inventory(state: Path, checkout: Path, keep: int) -> Plan:
    current = head(checkout)
    return plan(records(state), release_tags(), container_images(), current, keep)


@contextlib.contextmanager
def deployment_lock(state: Path) -> Iterator[None]:
    """Hold the controller's lock so no release starts mid-prune. Never creates it."""
    import fcntl  # Linux-only, imported here so the tests also run on Windows.

    try:
        handle = (state / "deployment.lock").open("r")
    except FileNotFoundError as exc:
        raise PruneError("No deployment lock exists; nothing was removed.") from exc
    with handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PruneError("A deployment is in progress; try again later.") from exc
        yield


def report(result: Plan, *, applying: bool) -> None:
    verb = "Removing" if applying else "Would remove"
    names = ", ".join(record.path.name for record in result.kept) or "none"
    print(f"Keeping {len(result.kept)} release record(s): {names}")
    print(f"Keeping {result.kept_tags} image tag(s) for current or kept revisions.")
    print(f"{verb} {len(result.records)} release record(s):")
    for record in result.records:
        print(f"  {record.path.name}")
    print(f"{verb} {len(result.tags)} image tag(s):")
    for tag in result.tags:
        print(f"  {tag.reference}")
    for record in result.skipped:
        print(
            f"Left in place: {record.path.name} still holds a source worktree; "
            "remove it with git worktree remove first."
        )
    if not applying:
        print("Dry run: nothing was removed. Repeat with --apply to remove these.")


def apply(result: Plan) -> int:
    """Untag first, then remove records. Each step is re-checked; failures continue."""
    failures = 0
    for tag in result.tags:
        try:
            # Never --force: Docker refuses to remove an image a container still uses.
            run("docker", "image", "rm", tag.reference)
        except PruneError:
            failures += 1
            print(f"Could not remove {tag.reference}.", file=sys.stderr)
    for record in result.records:
        if read_record(record.path) != record:
            failures += 1
            print(f"{record.path.name} changed; left in place.", file=sys.stderr)
            continue
        try:
            shutil.rmtree(record.path)
        except OSError:
            failures += 1
            print(f"Could not remove {record.path.name}.", file=sys.stderr)
    return failures


def keep_count(value: str) -> int:
    keep = int(value)
    if keep < MIN_KEEP:
        raise argparse.ArgumentTypeError(f"keep at least {MIN_KEEP} releases")
    return keep


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    command.add_argument(
        "--keep",
        type=keep_count,
        default=DEFAULT_KEEP,
        help=f"Newest release records to keep (default {DEFAULT_KEEP}, minimum {MIN_KEEP})",
    )
    mode = command.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true", help="List what would be removed (default)"
    )
    mode.add_argument(
        "--apply", action="store_true", help="Remove the listed records and image tags"
    )
    command.add_argument("--state-dir", type=Path, default=STATE)
    command.add_argument("--checkout", type=Path, default=CHECKOUT)
    return command


def main(argv: list[str] | None = None) -> int:
    options = parser().parse_args(argv)
    state = options.state_dir
    if state.is_symlink() or not state.is_dir():
        print("The deployment state directory must be an existing directory.")
        return 1
    try:
        if not options.apply:
            report(inventory(state, options.checkout, options.keep), applying=False)
            return 0
        with deployment_lock(state):
            result = inventory(state, options.checkout, options.keep)
            report(result, applying=True)
            failures = apply(result)
    except PruneError as exc:
        print(f"Prune stopped: {exc}", file=sys.stderr)
        return 1
    print("Prune finished." if not failures else f"{failures} removal(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
