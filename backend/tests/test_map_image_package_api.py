"""Map image packages bind inert uploaded pixels to authorised, exact saved revisions."""

import asyncio
import base64
import hashlib
import json
import threading
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest
from httpx import AsyncClient
from PIL import Image

from ase.adapters.reports.map_image import SavedMapImageRenderer
from ase.application.research import map_image
from ase.container import Container
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, bearer, login_token
from team_helpers import CONTEXT, team_service
from test_map_views_api import body
from test_report_team_scope import save_team_report, team_for


def image_request(size=(640, 360), image_format="PNG"):
    stream = BytesIO()
    Image.new("RGB", size, (8, 12, 20)).save(stream, format=image_format)
    return {
        "png_base64": base64.b64encode(stream.getvalue()).decode("ascii"),
        "include_annotations": False,
        "use_basis": "standard",
        "permitted_use": "",
    }


async def saved_view(client, container, user, *, team_id=None, basemap="dark"):
    report = await save_team_report(container, user, team_id)
    password = ADMIN_PASSWORD if user.email == ADMIN_EMAIL else USER_PASSWORD
    headers = bearer(await login_token(client, user.email, password))
    payload = body(report.id)
    payload["state"]["basemap"] = basemap
    response = await client.post("/api/map/views", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    saved = response.json()
    path = f"/api/map/views/{saved['view']['id']}/revisions/{saved['revision']['id']}/image-package"
    return path, headers, saved


async def test_exact_saved_map_exports_an_inert_attachment_package(
    client: AsyncClient, container: Container, user: User
) -> None:
    path, headers, saved = await saved_view(client, container, user)
    response = await client.post(path, headers=headers, json=image_request())
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    assert "attachment;" in response.headers["content-disposition"]
    assert "no-store" in response.headers["cache-control"]
    assert response.headers["x-content-type-options"] == "nosniff"
    with ZipFile(BytesIO(response.content)) as package:
        assert {"map.png", "manifest.json", "map-state.json"} <= set(package.namelist())
        with Image.open(BytesIO(package.read("map.png"))) as image:
            assert image.format == "PNG"
            assert image.width >= 640 and image.height >= 360
            image.load()
        manifest = json.loads(package.read("manifest.json"))
        assert manifest["revision"]["revision_id"] == saved["revision"]["id"]
        assert manifest["revision"]["report_version_number"] == 1
        assert manifest["input_dimensions"] == [640, 360]
        assert "not independently verified" in manifest["disclosure"]
        for name, receipt in manifest["members"].items():
            data = package.read(name)
            assert receipt == {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        state = json.loads(package.read("map-state.json"))
        # Canonical stored states omit legacy defaults exposed by the API schema.
        expected = {**saved["revision"]["state"]}
        expected.pop("measurement")
        expected.pop("time_basis")
        assert state == expected


async def test_private_image_export_requires_current_access_and_the_exact_revision(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    path, headers, saved = await saved_view(client, container, admin)
    payload = image_request()
    assert (await client.post(path, json=payload)).status_code == 401
    user_headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    assert (await client.post(path, headers=user_headers, json=payload)).status_code == 404
    wrong = path.replace(saved["revision"]["id"], str(uuid4()))
    assert (await client.post(wrong, headers=headers, json=payload)).status_code == 404
    other_path, _, other = await saved_view(client, container, admin)
    mixed = other_path.replace(other["revision"]["id"], saved["revision"]["id"])
    assert (await client.post(mixed, headers=headers, json=payload)).status_code == 404


async def test_removed_team_member_cannot_export_saved_pixels(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    team = await team_for(container, admin, user)
    path, headers, _ = await saved_view(client, container, user, team_id=team.id)
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    response = await client.post(path, headers=headers, json=image_request())
    assert response.status_code == 404


async def test_revocation_during_render_prevents_the_download(
    client: AsyncClient, container: Container, admin: User, user: User, monkeypatch
) -> None:
    team = await team_for(container, admin, user)
    path, headers, _ = await saved_view(client, container, user, team_id=team.id)
    started, release = threading.Event(), threading.Event()
    original = SavedMapImageRenderer.render

    def pause(self, *args):
        started.set()
        assert release.wait(10), "Test did not release the map rendering worker"
        return original(self, *args)

    monkeypatch.setattr(SavedMapImageRenderer, "render", pause)
    pending = asyncio.create_task(client.post(path, headers=headers, json=image_request()))
    try:
        assert await asyncio.to_thread(started.wait, 10), "Renderer was not reached"
        async with team_service(container) as service:
            await service.remove_member(admin, team.id, user.id, CONTEXT)
    finally:
        release.set()
    response = await pending
    assert response.status_code == 404
    assert response.headers.get("content-type") != "application/zip"


@pytest.mark.parametrize(
    "change",
    [
        {"png_base64": "invalid!"},
        {"png_base64": base64.b64encode(b"not an image").decode("ascii")},
        {"png_base64": ""},
        {"include_annotations": "false"},
        {"use_basis": "invented"},
        {"unexpected": True},
    ],
)
async def test_image_request_rejects_malformed_or_ambiguous_input(
    client: AsyncClient, container: Container, user: User, change: dict
) -> None:
    path, headers, _ = await saved_view(client, container, user)
    response = await client.post(path, headers=headers, json={**image_request(), **change})
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    ("size", "image_format"),
    [
        ((639, 360), "PNG"),
        ((640, 359), "PNG"),
        ((2049, 360), "PNG"),
        ((640, 2049), "PNG"),
        ((2048, 2048), "PNG"),
        ((640, 360), "JPEG"),
    ],
)
async def test_image_decoder_rejects_small_or_non_png_uploads(
    client: AsyncClient, container: Container, user: User, size: tuple, image_format: str
) -> None:
    path, headers, _ = await saved_view(client, container, user)
    response = await client.post(path, headers=headers, json=image_request(size, image_format))
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("basemap", ["satellite", "hybrid", "os_road"])
async def test_restricted_basemap_cannot_use_standard_export_basis(
    client: AsyncClient, container: Container, user: User, basemap: str
) -> None:
    path, headers, _ = await saved_view(client, container, user, basemap=basemap)
    response = await client.post(path, headers=headers, json=image_request())
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("authenticated", [False, True])
async def test_access_denial_does_not_consume_the_image_request_body(
    client: AsyncClient, container: Container, admin: User, user: User, authenticated: bool
) -> None:
    path, _, _ = await saved_view(client, container, admin)
    headers = {"Content-Type": "application/json"}
    if authenticated:
        headers.update(bearer(await login_token(client, user.email, USER_PASSWORD)))
    consumed = []

    async def payload():
        consumed.append(True)
        yield json.dumps(image_request()).encode()

    response = await client.post(path, headers=headers, content=payload())
    assert response.status_code == (404 if authenticated else 401), response.text
    assert consumed == []


async def test_capacity_denial_does_not_consume_the_image_request_body(
    client: AsyncClient, container: Container, user: User, monkeypatch
) -> None:
    path, headers, _ = await saved_view(client, container, user)
    headers["Content-Type"] = "application/json"
    monkeypatch.setattr(map_image, "_MAP_IMAGE_SLOTS", threading.BoundedSemaphore(0))
    consumed = []

    async def payload():
        consumed.append(True)
        yield json.dumps(image_request()).encode()

    response = await client.post(path, headers=headers, content=payload())
    assert response.status_code == 429, response.text
    assert consumed == []
