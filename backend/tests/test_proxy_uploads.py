"""Opt-in production-Caddy round trips against a disposable in-memory API fixture."""

from __future__ import annotations

import asyncio
import io
import json
import os
import socket
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
import uvicorn
from fastapi import FastAPI
from httpx import AsyncClient
from PIL import Image

from ase.api.middleware import AVATAR_MAX_BODY_BYTES, MAP_WORKSPACE_MAX_BODY_BYTES
from ase.domain.users import User
from helpers import USER_PASSWORD, bearer, login_token

pytestmark = pytest.mark.skipif(
    os.environ.get("ASE_CADDY_INTEGRATION") != "1",
    reason="Set ASE_CADDY_INTEGRATION=1 for isolated local Docker proxy checks",
)
IMAGE = (
    "caddy:2.11.4-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648"
)


async def docker(*args: str) -> str:
    process = await asyncio.create_subprocess_exec(
        "docker", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    output, error = await process.communicate()
    assert process.returncode == 0, error.decode()
    return output.decode().strip()


@pytest.fixture
async def proxy(app: FastAPI, tmp_path: Path) -> AsyncIterator[AsyncClient]:
    listener = socket.socket()
    listener.bind(("0.0.0.0", 0))  # noqa: S104, disposable fixture reached from Docker
    port = listener.getsockname()[1]
    listener.listen(128)
    server = uvicorn.Server(uvicorn.Config(app, lifespan="off", log_level="critical"))
    task = asyncio.create_task(server.serve(sockets=[listener]))
    name = "ase-kan153-proxy-" + uuid4().hex[:12]
    config = Path(__file__).resolve().parents[2] / "infra" / "Caddyfile"
    local = tmp_path / "Caddyfile"
    local.write_text(
        config.read_text().replace(
            "reverse_proxy api:8000", f"reverse_proxy host.docker.internal:{port}"
        )
    )
    extra = [] if os.name == "nt" else ["--add-host", "host.docker.internal:host-gateway"]
    started = False
    try:
        async with asyncio.timeout(20):
            while not server.started:
                await asyncio.sleep(0.01)
        await docker(
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "-p",
            "127.0.0.1::8080",
            *extra,
            "-e",
            "ASE_SITE_ADDRESS=http://localhost:8080",
            "-v",
            f"{local}:/etc/caddy/Caddyfile:ro",
            IMAGE,
        )
        started = True
        mapped = (await docker("port", name, "8080/tcp")).split(":")[-1]
        async with AsyncClient(
            base_url=f"http://127.0.0.1:{mapped}", timeout=10, headers={"Host": "localhost:8080"}
        ) as client:
            async with asyncio.timeout(20):
                while True:
                    try:
                        if (await client.get("/api/health")).status_code == 200:
                            break
                    except OSError:
                        pass
                    await asyncio.sleep(0.05)
            yield client
    finally:
        if started:
            await docker("rm", "-f", name)
        server.should_exit = True
        await task
        listener.close()


async def test_supported_uploads_cross_proxy_and_excess_stays_bounded(
    proxy: AsyncClient, client: AsyncClient, user: User
) -> None:
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    image = io.BytesIO()
    Image.new("RGB", (256, 256), "red").save(image, format="PNG", compress_level=0)
    assert 65536 < len(image.getvalue()) < AVATAR_MAX_BODY_BYTES
    avatar = "/api/me/directory-profile/avatar"
    response = await proxy.put(
        avatar,
        content=image.getvalue(),
        headers={**headers, "Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["avatar_url"]
    unauthenticated = await proxy.put(
        avatar, content=image.getvalue(), headers={"Content-Type": "application/octet-stream"}
    )
    assert "authorization" not in unauthenticated.request.headers
    assert unauthenticated.status_code == 401, (
        unauthenticated.status_code,
        unauthenticated.headers.get("content-type"),
        unauthenticated.text[:100],
    )
    objects = [
        {
            "id": str(index),
            "name": "Point",
            "shape": "point",
            "anchors": [[0, 0]],
            "colour": "#ff0000",
            "visible": True,
            "locked": False,
            "notes": "n" * 1800,
        }
        for index in range(45)
    ]
    payload = {"version": 1, "objects": objects, "selectedId": None}
    body = {"kind": "drawings", "title": "Proxy regression", "payload": payload}
    assert 65536 < len(json.dumps(body)) < MAP_WORKSPACE_MAX_BODY_BYTES
    created = await proxy.post("/api/map/workspaces", json=body, headers=headers)
    assert created.status_code == 201, created.text
    path = "/api/map/workspaces/" + created.json()["id"]
    updated = await proxy.patch(
        path, json={"title": "Updated", "payload": payload, "expected_revision": 1}, headers=headers
    )
    assert updated.status_code == 200, updated.text
    for route, method, limit in [
        (avatar, "PUT", AVATAR_MAX_BODY_BYTES),
        ("/api/map/workspaces", "POST", MAP_WORKSPACE_MAX_BODY_BYTES),
    ]:
        for authenticated in [True, False]:
            selected = (
                {**headers, "Content-Type": "application/octet-stream"} if authenticated else {}
            )
            response = await proxy.request(
                method, route, content=b"x" * (limit + 1), headers=selected
            )
            assert response.status_code == 413

        async def chunks(size: int = limit) -> AsyncIterator[bytes]:
            yield b"x" * size
            yield b"x"

        response = await proxy.request(
            method,
            route,
            content=chunks(),
            headers={**headers, "Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 413
    assert (await proxy.post(avatar, content=b"x" * 65537, headers=headers)).status_code == 413
