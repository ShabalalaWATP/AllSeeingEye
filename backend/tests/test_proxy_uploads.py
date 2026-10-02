"""Opt-in real-Caddy round trips inside a network-disabled Linux pytest container.

Set ASE_CADDY_INTEGRATION=1 and ASE_CADDY_TEST_CONTAINER to this runner's name.
The runner needs Docker CLI/socket access, its default hostname, --network none
and --label ase.kan153.test-runner=true. Caddy shares only its loopback namespace.
Cache the pinned Caddy image first; this fixture never pulls an image.
Native Windows/macOS opt-ins are unsupported; use this isolated Linux runner on
Docker Desktop instead. No host networking support or published ports are needed.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import socket
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI
from httpx import AsyncClient, ConnectError, Limits
from PIL import Image

from ase.api.middleware import AVATAR_MAX_BODY_BYTES, MAP_WORKSPACE_MAX_BODY_BYTES
from ase.domain.users import User
from helpers import USER_PASSWORD, bearer, login_token
from proxy_test_docker import docker, owned_proxy
from proxy_test_network import isolated_runner_id, loopback_caddy_config, loopback_listener

pytestmark = pytest.mark.skipif(
    os.environ.get("ASE_CADDY_INTEGRATION") != "1",
    reason="Set ASE_CADDY_INTEGRATION=1 for isolated local Docker proxy checks",
)
IMAGE = (
    "caddy:2.11.4-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648"
)


@pytest.fixture
async def proxy(app: FastAPI, tmp_path: Path) -> AsyncIterator[AsyncClient]:
    runner = os.environ.get("ASE_CADDY_TEST_CONTAINER")
    if sys.platform != "linux" or not runner:
        pytest.fail("Opt-in requires ASE_CADDY_TEST_CONTAINER in an isolated Linux runner.")
    details = json.loads(await docker("inspect", runner))
    namespace = isolated_runner_id(details[0], socket.gethostname())
    listener = loopback_listener()
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, lifespan="off", log_level="critical"))
    task = asyncio.create_task(server.serve(sockets=[listener]))
    config = Path(__file__).resolve().parents[2] / "infra" / "Caddyfile"
    local = tmp_path / "Caddyfile"
    try:
        local.write_text(loopback_caddy_config(config.read_text(), port))
        with loopback_listener() as reservation:
            proxy_port = reservation.getsockname()[1]
        async with asyncio.timeout(20):
            while not server.started:
                await asyncio.sleep(0.01)
        async with (
            owned_proxy(namespace, IMAGE, proxy_port, local),
            AsyncClient(
                base_url=f"http://127.0.0.1:{proxy_port}",
                timeout=10,
                headers={"Host": f"localhost:{proxy_port}"},
                trust_env=False,
                # An early 413 may close a connection before draining the upload.
                limits=Limits(max_keepalive_connections=0),
            ) as client,
        ):
            async with asyncio.timeout(20):
                while True:
                    try:
                        if (await client.get("/api/health")).status_code == 200:
                            break
                    except (OSError, ConnectError):
                        pass
                    await asyncio.sleep(0.05)
            yield client
    finally:
        try:
            server.should_exit = True
            await asyncio.wait_for(task, timeout=10)
        finally:
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
