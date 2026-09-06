"""Frozen package integrity, geographic honesty, resource limits and late revocation."""

import asyncio
import hashlib
import io
import json
import zipfile
from dataclasses import replace
from threading import Event
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.adapters.reports.evidence_package import (
    MAX_PACKAGE_BYTES,
    FrozenEvidencePackageRenderer,
    evidence_geojson,
)
from ase.application.reports.evidence_package import _PACKAGE_SLOTS, ExportEvidencePackage
from ase.domain.errors import Forbidden, InvalidRequest, RateLimited
from report_documents_helpers import document_records


def test_package_has_verifiable_digests_and_unicode_without_fetching_originals() -> None:
    record, version = document_records()
    version = replace(version, markdown="# گزارش\n尚未確認交付。\n")
    renderer = FrozenEvidencePackageRenderer()
    content = renderer.render(record, version)
    assert renderer.render(record, version) == content
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert set(archive.namelist()) == {
            "report.md",
            "report.json",
            "analysis.json",
            "evidence.json",
            "evidence.geojson",
            "manifest.json",
            "README.txt",
        }
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["version_id"] == str(version.id)
        assert manifest["original_assets_included"] is False
        for item in manifest["files"]:
            value = archive.read(item["path"])
            assert hashlib.sha256(value).hexdigest() == item["sha256"]
            assert len(value) == item["bytes"]
        assert archive.read("report.md").decode("utf-8") == version.markdown
        evidence = json.loads(archive.read("evidence.json"))
        assert evidence[0]["content_hash"] == version.evidence[0].content_hash
        assert b"not source authenticity" in archive.read("README.txt")


@pytest.mark.parametrize("precision", [None, "country", "none", "invalid"])
def test_country_and_unknown_precision_do_not_export_incident_points(precision: str | None) -> None:
    _, version = document_records()
    item = replace(version.evidence[0], lon=37.0, lat=55.0, geo_confidence=precision)
    feature = evidence_geojson(replace(version, evidence=(item,)))["features"][0]
    assert feature["geometry"] is None
    assert feature["properties"]["precision"] == precision


@pytest.mark.parametrize("lon,lat", [(float("nan"), 0), (181, 0), (0, 91)])
def test_invalid_points_remain_unlocated(lon: float, lat: float) -> None:
    _, version = document_records()
    item = replace(version.evidence[0], lon=lon, lat=lat, geo_confidence="exact")
    assert evidence_geojson(replace(version, evidence=(item,)))["features"][0]["geometry"] is None


def test_valid_zero_and_antimeridian_coordinates_are_preserved() -> None:
    _, version = document_records()
    for lon in (0.0, -180.0, 180.0):
        item = replace(version.evidence[0], lon=lon, lat=0.0, geo_confidence="city")
        feature = evidence_geojson(replace(version, evidence=(item,)))["features"][0]
        assert feature["geometry"]["coordinates"] == [lon, 0.0]
        assert feature["properties"]["location_role"] == "unknown"


def test_package_refuses_oversized_or_mismatched_version() -> None:
    record, version = document_records()
    renderer = FrozenEvidencePackageRenderer()
    with pytest.raises(InvalidRequest):
        renderer.render(record, replace(version, report_id=uuid4()))
    with pytest.raises(InvalidRequest, match="8 MiB"):
        renderer.render(record, replace(version, markdown="a" * MAX_PACKAGE_BYTES))


async def test_export_rechecks_resolved_version_before_releasing_bytes() -> None:
    record, version = document_records()
    reader = AsyncMock()
    reader.execute.return_value = (record, version)
    actor = AsyncMock()
    exporter = ExportEvidencePackage(reader, FrozenEvidencePackageRenderer())
    result = await exporter.execute(actor, record.id)
    assert result.media_type == "application/zip"
    reader.recheck.assert_awaited_once_with(actor, record.id, version.number)
    reader.recheck.side_effect = Forbidden()
    with pytest.raises(Forbidden):
        await exporter.execute(actor, record.id, version.number)
    with pytest.raises(InvalidRequest):
        await exporter.execute(actor, record.id, 0)


async def test_busy_exports_reject_without_queuing_and_cancellation_retains_worker_slot() -> None:
    record, version = document_records()
    reader = AsyncMock()
    reader.execute.return_value = (record, version)
    release = Event()
    started = Event()

    class BlockingRenderer:
        def render(self, *_: object) -> bytes:
            started.set()
            assert release.wait(5)
            return b"fixture"

    exporter = ExportEvidencePackage(reader, BlockingRenderer())
    first = asyncio.create_task(exporter.execute(AsyncMock(), record.id))
    second = asyncio.create_task(exporter.execute(AsyncMock(), record.id))
    try:
        await asyncio.to_thread(started.wait, 2)
        await asyncio.sleep(0)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        with pytest.raises(RateLimited):
            await exporter.execute(AsyncMock(), record.id)
    finally:
        release.set()
        await second
    # Wait for both worker finally blocks, without assuming scheduling order.

    for _ in range(100):
        if _PACKAGE_SLOTS.acquire(blocking=False):
            if _PACKAGE_SLOTS.acquire(blocking=False):
                _PACKAGE_SLOTS.release()
                _PACKAGE_SLOTS.release()
                break
            _PACKAGE_SLOTS.release()
        await asyncio.sleep(0.01)
    else:
        pytest.fail("Cancelled export leaked an admission slot")
