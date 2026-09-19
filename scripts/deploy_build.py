"""Build private release contexts with files readable by non-root image users."""

from collections.abc import Callable
from pathlib import Path


def build_images(sha: str, worktree: Path, run: Callable[..., str]) -> dict[str, str]:
    # The enclosing release directory stays 0700. Only the Git child uses 0022,
    # otherwise Docker COPY preserves 0600 files that the runtime users cannot read.
    run("git", "worktree", "add", "--detach", str(worktree), sha, mask=0o022)
    api = f"ase-api:release-{sha}"
    web = f"ase-web:release-{sha}"
    label = f"org.opencontainers.image.revision={sha}"
    run("docker", "build", "--label", label, "-t", api, "backend", cwd=worktree)
    run(
        "docker",
        "build",
        "--label",
        label,
        "-t",
        web,
        "-f",
        "frontend/Dockerfile",
        ".",
        cwd=worktree,
    )
    api_id = run("docker", "image", "inspect", "--format", "{{.Id}}", api)
    web_id = run("docker", "image", "inspect", "--format", "{{.Id}}", web)
    # These probes retain each image's USER, have no network or production mounts,
    # and fail before backup/cutover if the built runtime cannot read its own files.
    run(
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--entrypoint",
        "python",
        api_id,
        "-I",
        "-c",
        "import ase.infrastructure.migrations; import ase.adapters.research_imports.service; "
        "from pathlib import Path; "
        "[Path(p).read_bytes() for p in "
        "('/app/src/ase/main.py', '/app/src/ase/cli.py', '/app/alembic.ini')]",
    )
    run(
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--entrypoint",
        "sh",
        web_id,
        "-c",
        "test -r /etc/caddy/Caddyfile && test -r /srv/index.html",
    )
    return {"api": api_id, "parser": api_id, "web": web_id}
