"""Bounded Docker commands and exact ownership cleanup for the Caddy test sidecar."""

import asyncio
import json
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from uuid import uuid4


async def docker(*args: str, timeout: float = 30) -> str:
    process = await asyncio.create_subprocess_exec(
        "docker", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    communication = asyncio.create_task(process.communicate())

    async def reap() -> None:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                process.kill()
        await communication

    try:
        output, error = await asyncio.wait_for(asyncio.shield(communication), timeout)
    except asyncio.CancelledError:
        # Let an in-flight create acknowledge before ownership reconciliation.
        try:
            await asyncio.wait_for(asyncio.shield(communication), timeout)
        except TimeoutError:
            await reap()
        raise
    except BaseException:
        await reap()
        raise
    assert process.returncode == 0, error.decode()
    return output.decode().strip()


async def remove_owned_proxy(namespace: str, token: str) -> None:
    """Reconcile even an unacknowledged create, without deleting by container name."""
    identifiers = await docker(
        "ps", "-aq", "--no-trunc", "--filter", f"label=ase.kan153.fixture={token}"
    )
    for identifier in identifiers.splitlines():
        if re.fullmatch(r"[0-9a-f]{64}", identifier) is None:
            raise ValueError("Invalid test container identity; refusing cleanup.")
        details = json.loads(await docker("inspect", identifier))[0]
        labels = details.get("Config", {}).get("Labels") or {}
        if (
            details.get("Id") != identifier
            or labels.get("ase.kan153.fixture") != token
            or labels.get("ase.kan153.runner") != namespace
            or details.get("HostConfig", {}).get("NetworkMode") != f"container:{namespace}"
        ):
            raise ValueError("Test container ownership differs; refusing cleanup.")
        # -v removes only anonymous volumes attached to this verified owned container.
        await docker("rm", "-f", "-v", identifier)


@asynccontextmanager
async def owned_proxy(namespace: str, image: str, port: int, config: Path) -> AsyncIterator[None]:
    token = uuid4().hex
    name = f"ase-kan153-proxy-{token}"
    try:
        identifier = await docker(
            "create",
            "--pull=never",
            "--name",
            name,
            "--network",
            f"container:{namespace}",
            "--label",
            f"ase.kan153.runner={namespace}",
            "--label",
            f"ase.kan153.fixture={token}",
            "-e",
            f"ASE_SITE_ADDRESS=http://localhost:{port}",
            image,
        )
        if re.fullmatch(r"[0-9a-f]{64}", identifier) is None:
            raise ValueError("Docker did not return the owned test container ID.")
        await docker("cp", str(config), f"{identifier}:/etc/caddy/Caddyfile")
        await docker("start", identifier)
        yield
    finally:
        cleanup = asyncio.create_task(remove_owned_proxy(namespace, token))
        try:
            await asyncio.shield(cleanup)
        except asyncio.CancelledError:
            await cleanup
            raise
