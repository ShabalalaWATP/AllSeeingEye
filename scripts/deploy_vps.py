"""Restricted, serial application deployment for the existing ASE VPS.

Installed root-owned under /usr/local/lib/ase-deploy; runs as the ase account.
No application secrets are accepted from GitHub. See docs/AUTOMATIC_DEPLOYMENT.md.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path("/home/ase/ase")
STATE = Path("/home/ase/deployments")
KEY = Path("/home/ase/.config/all-seeing-eye/backup-auth.key")
SITE = "https://allseeingeyeosint.com"
CURL = ("curl", "--silent", "--show-error", "--max-time", "15")
SERVICES = ("api", "parser", "web")
MANUAL_PATHS = (
    "docker-compose.yml",
    "compose.yml",
    "compose.yaml",
    "docker-compose.yaml",
    "backend/alembic/",
    "backend/alembic.ini",
    "backend/src/ase/infrastructure/migrations.py",
    "backend/src/ase/cli.py",
    "scripts/deploy_vps.py",
    "scripts/deploy_ssh.py",
)


class DeploymentError(RuntimeError):
    """A deployment was refused or did not complete safely."""


def run(*args: str, cwd: Path = ROOT, timeout: int = 1200) -> str:
    # Capture output: dependency/build tools and Compose can print sensitive values.
    # Errors report the operation only, never subprocess output or environment.
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.SubprocessError, OSError, UnicodeError) as exc:
        raise DeploymentError(
            f"Operation failed: {args[0]} {args[1] if len(args) > 1 else ''}"
        ) from exc
    return result.stdout.strip()


def git(*args: str) -> str:
    return run("git", *args)


def require_clean() -> None:
    if git("status", "--porcelain"):
        raise DeploymentError(
            "VPS checkout contains local changes; operator review required."
        )
    if git("branch", "--show-current") != "main":
        raise DeploymentError("VPS checkout must be on main.")


def require_latest(sha: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise DeploymentError("Expected a full lowercase Git commit SHA.")
    git("fetch", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main")
    if git("rev-parse", "origin/main") != sha:
        raise DeploymentError("Requested revision is no longer the head of main.")


def require_compatible(previous: str, sha: str) -> None:
    git("merge-base", "--is-ancestor", previous, sha)
    paths = git("diff", "--name-only", previous, sha).splitlines()
    # Controller upgrades are allowed only after an operator installs that exact
    # reviewed version in the root-owned directory. Repository code cannot replace it.
    for name in ("deploy_vps.py", "deploy_ssh.py"):
        path = f"scripts/{name}"
        if path in paths:
            installed = Path(__file__).with_name(name).read_text().strip()
            if git("show", f"{sha}:{path}") == installed:
                paths.remove(path)
    if any(
        path == rule or path.startswith(rule) for path in paths for rule in MANUAL_PATHS
    ):
        raise DeploymentError(
            "Migration, Compose or deployment-controller change requires manual rollout."
        )


def compose(*args: str) -> str:
    return run(
        "docker",
        "compose",
        "--project-name",
        "ase",
        "-f",
        str(ROOT / "docker-compose.yml"),
        *args,
    )


def current_images() -> dict[str, str]:
    images = {}
    for service in SERVICES:
        container = compose("ps", "-q", service)
        if not container or "\n" in container:
            raise DeploymentError(f"Expected one running {service} container.")
        images[service] = run("docker", "inspect", "--format", "{{.Image}}", container)
    return images


def smoke() -> None:
    for path, status in (("/api/health", "ok"), ("/api/ready", "ready")):
        try:
            body = json.loads(run(*CURL, "--fail", SITE + path))
        except ValueError as exc:
            raise DeploymentError("Health endpoint returned invalid JSON.") from exc
        if not isinstance(body, dict) or body.get("status") != status:
            raise DeploymentError("Health endpoint did not report success.")
    page = run(*CURL, "--fail", SITE + "/")
    asset = re.search(r'src="(/assets/[^"\s]+\.js)"', page)
    if not asset:
        raise DeploymentError("Frontend entry point is missing.")
    run(*CURL, "--fail", "--output", "/dev/null", SITE + asset[1])
    code = run(
        *CURL,
        "--output",
        "/dev/null",
        "--write-out",
        "%{http_code}",
        SITE + "/api/admin/sources",
    )
    if code != "401":
        raise DeploymentError("Unauthenticated administration check failed.")


def wait_healthy(images: dict[str, str]) -> None:
    for attempt in range(12):
        try:
            for service, expected in images.items():
                container = compose("ps", "-q", service)
                actual = run(
                    "docker",
                    "inspect",
                    "--format",
                    "{{.Image}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
                    container,
                )
                health = "none" if service == "web" else "healthy"
                if actual != f"{expected} running {health}":
                    raise DeploymentError(f"Unexpected running image for {service}.")
            smoke()
            return
        except DeploymentError:
            if attempt == 11:
                raise
            time.sleep(5)


def start(images: dict[str, str]) -> None:
    for service, image in images.items():
        run("docker", "image", "tag", image, f"ase-{service}:latest")
    # The database is deliberately excluded. API and parser must be the same release.
    compose(
        "up",
        "-d",
        "--no-deps",
        "--no-build",
        "--wait",
        "--wait-timeout",
        "180",
        *SERVICES,
    )


def build(sha: str, worktree: Path) -> dict[str, str]:
    print(
        "Building application images while the current release stays online.",
        flush=True,
    )
    git("worktree", "add", "--detach", str(worktree), sha)
    api = f"ase-api:release-{sha}"
    web = f"ase-web:release-{sha}"
    run(
        "docker",
        "build",
        "--label",
        f"org.opencontainers.image.revision={sha}",
        "-t",
        api,
        "backend",
        cwd=worktree,
    )
    run(
        "docker",
        "build",
        "--label",
        f"org.opencontainers.image.revision={sha}",
        "-t",
        web,
        "-f",
        "frontend/Dockerfile",
        ".",
        cwd=worktree,
    )
    api_id = run("docker", "image", "inspect", "--format", "{{.Id}}", api)
    web_id = run("docker", "image", "inspect", "--format", "{{.Id}}", web)
    return {"api": api_id, "parser": api_id, "web": web_id}


def backup(destination: Path) -> None:
    print("Creating and verifying the pre-deployment database backup.", flush=True)
    run(
        "python3",
        "scripts/backup.py",
        "postgres",
        "--authentication-key-file",
        str(KEY),
        "--output",
        str(destination),
    )
    run(
        "python3",
        "scripts/restore.py",
        str(destination),
        "--authentication-key-file",
        str(KEY),
        "--verify-only",
    )


def rollout(
    sha: str, previous: str, images: dict[str, str], old: dict[str, str]
) -> None:
    # Fetch again after the potentially lengthy build. Never replace a newer main.
    require_latest(sha)
    require_clean()
    if git("rev-parse", "HEAD") != previous:
        raise DeploymentError("VPS checkout changed during build.")
    try:
        git("merge", "--ff-only", sha)
        start(images)
        wait_healthy(images)
    except (DeploymentError, KeyboardInterrupt):
        print("Cutover failed; restoring the previous application release.", flush=True)
        # Reset only our own clean fast-forward; never discard an operator's changes.
        require_clean()
        if git("rev-parse", "HEAD") not in (sha, previous):
            raise DeploymentError(
                "Rollback refused: checkout changed during deployment."
            )
        git("reset", "--hard", previous)
        start(old)
        wait_healthy(old)
        raise DeploymentError(
            "Deployment failed; previous application release restored."
        ) from None


def deploy(sha: str, *, check_only: bool = False) -> None:
    require_latest(sha)
    require_clean()
    previous = git("rev-parse", "HEAD")
    require_compatible(previous, sha)
    if not KEY.is_file() or shutil.disk_usage(ROOT).free < 6 * 1024**3:
        raise DeploymentError("Backup key missing or fewer than 6 GiB free on the VPS.")
    old = current_images()
    if check_only:
        print(f"Preflight passed for {sha}. No release was changed.", flush=True)
        return
    if previous == sha:
        labels = [
            run(
                "docker",
                "image",
                "inspect",
                "--format",
                '{{index .Config.Labels "org.opencontainers.image.revision"}}',
                image,
            )
            for image in old.values()
        ]
        if all(label == sha for label in labels):
            wait_healthy(old)
            print(f"Already deployed and healthy: {sha}", flush=True)
            return
    release = Path(tempfile.mkdtemp(prefix=f"{sha[:12]}-", dir=STATE))
    worktree = release / "source"
    record = {"previous": previous, "target": sha, "rollback_images": old}
    (release / "release.json").write_text(json.dumps(record, indent=2) + "\n")
    for service, image in old.items():
        run("docker", "image", "tag", image, f"ase-{service}:rollback-{previous}")
    try:
        images = build(sha, worktree)
        backup(release / "backup")
        rollout(sha, previous, images, old)
        (release / "success").write_text(sha + "\n")
        print(f"Deployment healthy: {sha}. Recovery record: {release}", flush=True)
    finally:
        if worktree.exists():
            # Only remove the temporary worktree created by this invocation.
            with contextlib.suppress(DeploymentError):
                git("worktree", "remove", "--force", str(worktree))


def interrupted(signum: int, _frame: object) -> None:
    raise DeploymentError(f"Deployment interrupted by signal {signum}.")


def main(sha: str, *, check_only: bool = False) -> int:
    import fcntl  # Linux-only host lock, imported here so tests also run on Windows.

    os.umask(0o077)
    STATE.mkdir(mode=0o700, exist_ok=True)
    with (STATE / "deployment.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another VPS deployment is in progress.", file=sys.stderr)
            return 1
        for sig in (signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, interrupted)
        try:
            deploy(sha, check_only=check_only)
        except (DeploymentError, OSError) as exc:
            print(f"Deployment stopped: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: deploy_vps.py FULL_SHA")
    sys.exit(main(sys.argv[1]))
