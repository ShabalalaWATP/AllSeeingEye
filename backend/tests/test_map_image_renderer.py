"""Renderer privacy, parser bounds and admission ownership regressions."""

import asyncio
import base64
import io
import json
import threading
import zipfile
import zlib
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from PIL import Image, PngImagePlugin

from ase.adapters.reports.map_image import SavedMapImageRenderer
from ase.adapters.reports.map_image_footer import image_footer
from ase.application.ports.map_image import MapImageOptions
from ase.application.research import map_image
from ase.domain.errors import InvalidRequest, RateLimited, Unauthenticated
from ase.domain.map_measurement import MapMeasurement
from ase.domain.map_views import MapCamera, MapView, MapViewRevision, MapViewState
from test_map_body_limits import send_body


def fixture_map():
    now = datetime.now(UTC)
    view = MapView(uuid4(), uuid4(), uuid4(), None, uuid4(), now)
    state = MapViewState(MapCamera(10, 50, 4))
    revision = MapViewRevision(
        view.latest_revision_id,
        view.id,
        1,
        "Map",
        uuid4(),
        1,
        state,
        "a" * 64,
        "b" * 64,
        view.created_by,
        now,
    )
    output = io.BytesIO()
    meta = PngImagePlugin.PngInfo()
    meta.add_text("private", "secret image metadata", zip=True)
    Image.new("RGB", (640, 360), "navy").save(output, format="PNG", pnginfo=meta)
    options = MapImageOptions(base64.b64encode(output.getvalue()).decode())
    return view, revision, options, now


def test_render_removes_metadata_and_private_measurement():
    view, revision, options, now = fixture_map()
    revision = replace(
        revision,
        state=replace(
            revision.state, measurement=MapMeasurement("distance", ((10.0, 20.0), (11.0, 21.0)))
        ),
    )
    data = SavedMapImageRenderer().render(view, revision, options, now)
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        state = json.loads(package.read("map-state.json"))
        assert "measurement" not in state
        with Image.open(io.BytesIO(package.read("map.png"))) as image:
            assert not image.info
            assert image.height > 360
            manifest = json.loads(package.read("manifest.json"))
            assert manifest["output_dimensions"] == list(image.size)
            assert manifest["input_dimensions"] == [640, 360]
        assert b"secret image metadata" not in b"".join(package.read(n) for n in package.namelist())


@pytest.mark.parametrize("suffix", [b"trailing", b"\x00"])
def test_png_trailing_data_rejected(suffix):
    view, revision, options, now = fixture_map()
    options = replace(
        options, png_base64=base64.b64encode(base64.b64decode(options.png_base64) + suffix).decode()
    )
    with pytest.raises(InvalidRequest):
        SavedMapImageRenderer().render(view, revision, options, now)


@pytest.mark.parametrize("include,basis", [(True, "standard"), (False, "licensed")])
def test_declaration_required_for_private_annotations_and_nonstandard_basis(include, basis):
    view, revision, options, now = fixture_map()
    with pytest.raises(InvalidRequest, match="permitted-use"):
        SavedMapImageRenderer().render(
            view, revision, replace(options, include_annotations=include, use_basis=basis), now
        )


async def test_image_body_allowance_is_exact_and_chunked_bounded():
    path = f"/api/map/views/{uuid4()}/revisions/{uuid4()}/image-package"
    assert (await send_body(path, "POST", [b"x" * 70000]))[0] == 204
    assert (await send_body(path, "PATCH", [b"x" * 70000]))[0] == 413
    assert (await send_body(path + "/extra", "POST", [b"x" * 70000]))[0] == 413
    assert (await send_body(path, "POST", [b"x" * (12 * 1024 * 1024 + 1)]))[0] == 413


async def test_cancelled_render_keeps_admission_until_worker_exits(monkeypatch):
    view, revision, options, now = fixture_map()
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(map_image, "_MAP_IMAGE_SLOTS", slots)
    started, release = threading.Event(), threading.Event()

    def render(*args):
        started.set()
        assert release.wait(10)
        return b"zip"

    views = SimpleNamespace(clock=SimpleNamespace(now=lambda: now))
    service = map_image.ExportMapImage(views, SimpleNamespace(render=render))

    async def execute():
        with service.admission():
            await service.execute(SimpleNamespace(expires_at=now), (view, revision), options)

    pending = asyncio.create_task(execute())
    try:
        assert await asyncio.to_thread(started.wait, 10)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        with pytest.raises(RateLimited), service.admission():
            pass
    finally:
        release.set()
        if service.task is not None:
            await service.task
        await asyncio.sleep(0)
    with service.admission():
        pass


async def test_token_expiry_after_final_read_prevents_release():
    view, revision, options, now = fixture_map()
    views = SimpleNamespace(
        clock=SimpleNamespace(now=lambda: now),
        uow=SimpleNamespace(rollback=AsyncMock()),
        get=AsyncMock(return_value=(view, revision)),
    )
    service = map_image.ExportMapImage(views, SimpleNamespace(render=lambda *args: b"zip"))
    with service.admission(), pytest.raises(Unauthenticated):
        await service.execute(SimpleNamespace(expires_at=now), (view, revision), options)


@pytest.mark.parametrize("change", ["duplicate_header", "animation", "crc", "truncated"])
def test_png_structure_rejected_before_decoding(change):
    view, revision, options, now = fixture_map()
    data = base64.b64decode(options.png_base64)
    if change == "duplicate_header":
        data = data[:33] + data[8:33] + data[33:]
    elif change == "animation":
        kind, value = b"acTL", (2).to_bytes(4, "big") + bytes(4)
        chunk = len(value).to_bytes(4, "big") + kind + value
        chunk += zlib.crc32(kind + value).to_bytes(4, "big")
        data = data[:33] + chunk + data[33:]
    elif change == "crc":
        data = data[:29] + bytes(4) + data[33:]
    else:
        data = data[:-8]
    with pytest.raises(InvalidRequest):
        SavedMapImageRenderer().render(
            view, revision, replace(options, png_base64=base64.b64encode(data).decode()), now
        )


def test_output_including_footer_is_bounded_and_nonlatin_credit_is_explicit():
    with pytest.raises(InvalidRequest, match="attribution footer"):
        image_footer(Image.new("RGB", (2048, 1900)), ["A credit"] * 20)
    # Packaged Cyrillic/CJK glyphs and explicit unsupported-glyph receipt must not crash.
    result = image_footer(Image.new("RGB", (640, 360)), ["Картография 中文 مرجع"])
    with Image.open(io.BytesIO(result)) as image:
        assert image.height < 2048 and image.width * image.height <= 4_000_000


@pytest.mark.parametrize(
    "basemap,basis,expected",
    [
        ("satellite", "noncommercial", "Copernicus Sentinel data 2024"),
        ("hybrid", "licensed", "EOX IT Services"),
        ("os_road", "licensed", "Crown copyright and database rights 2026"),
    ],
)
def test_restricted_exports_preserve_current_basemap_and_full_attribution(basemap, basis, expected):
    view, revision, options, now = fixture_map()
    revision = replace(revision, state=replace(revision.state, basemap=basemap))
    options = replace(options, use_basis=basis, permitted_use="Operator confirms permitted purpose")
    result = SavedMapImageRenderer().render(view, revision, options, now)
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        credits = " ".join(manifest["attributions"])
        assert expected in credits
        assert "OpenMapTiles" in credits and "openstreetmap.org/copyright" in credits
        assert json.loads(archive.read("map-state.json"))["basemap"] == basemap
