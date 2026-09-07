"""Sanitise bounded PNG pixels and package verified metadata, without fetching map URLs."""

import base64
import binascii
import hashlib
import io
import json
import struct
import warnings
import zipfile
import zlib
from datetime import datetime
from typing import Any

from PIL import Image, UnidentifiedImageError

from ase.adapters.reports.map_image_footer import image_footer
from ase.application.ports.map_image import (
    MAX_MAP_IMAGE_BYTES,
    MAX_MAP_PACKAGE_BYTES,
    MapImageOptions,
)
from ase.domain.errors import InvalidRequest
from ase.domain.map_view_records import state_to_dict
from ase.domain.map_views import MapView, MapViewRevision

POLICY = "ase-client-map-image-v1"
OSM = "(c) OpenStreetMap contributors https://www.openstreetmap.org/copyright"
EOX = (
    "Sentinel-2 cloudless by EOX IT Services GmbH, contains modified Copernicus Sentinel "
    "data 2024. CC BY-NC-SA 4.0 https://cloudless.eox.at/documentation/license"
)
DISCLAIMER = (
    "Client-rendered pixels are not independently verified against the saved map state. "
    "Hashes identify exported bytes, not authenticity. Basemap imagery is current at export, "
    "not historical evidence. The server receipt time is not a verified image capture time. "
    "Redaction applies only to saved overlays, AOI and measurement metadata when excluded; "
    "frozen evidence locations remain. Pixel redaction is not independently verified. "
    "Permitted use is an operator assertion, not legal verification. "
    "Points are evidence locations; country-level positions are approximate. Unsupported "
    "geometry is omitted; flat maps omit polar geometry beyond +/-85.05112878 degrees. "
    "Display geometry is simplified; included saved annotations retain canonical geometry "
    "in map-state.json. "
    "Unsupported attribution glyphs are represented by explicit Unicode code points."
)


def _attributions(basemap: str, options: MapImageOptions) -> list[str]:
    if (options.include_annotations or options.use_basis != "standard") and not (
        options.permitted_use.strip()
    ):
        raise InvalidRequest("Provide a permitted-use statement for this export choice.")
    if basemap.startswith("os_"):
        if options.use_basis != "licensed":
            raise InvalidRequest("Ordnance Survey exports require a licensed-use declaration.")
        return [
            "Contains OS data (c) Crown copyright and database rights 2026.",
            "OpenFreeMap",
            "(c) OpenMapTiles",
            OSM,
        ]
    credits = ["OpenFreeMap", "(c) OpenMapTiles", OSM]
    if basemap in {"satellite", "hybrid"}:
        if options.use_basis == "standard":
            raise InvalidRequest("EOX imagery requires noncommercial or licensed-use declaration.")
        credits = [EOX, *credits]
    return credits


def _dimensions(header: bytes) -> None:
    width, height = struct.unpack(">II", header)
    if not (640 <= width <= 2048 and 360 <= height <= 2048):
        raise ValueError("PNG dimensions must be 640x360 to 2048x2048")
    if width * height > 4_000_000:
        raise ValueError("PNG pixel count exceeds four million")


def _sanitise_png(data: bytes) -> bytes:
    if len(data) > MAX_MAP_IMAGE_BYTES or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("PNG size or signature")
    # Inspect structure before decoder allocation. Reject animations and trailing data.
    offset = 8
    ended = False
    sanitised = bytearray(data[:8])
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset : offset + 4], "big")
        kind = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(data) or kind in {b"acTL", b"fcTL", b"fdAT"}:
            raise ValueError("Invalid or animated PNG")
        expected_crc = int.from_bytes(data[end - 4 : end], "big")
        if zlib.crc32(data[offset + 4 : end - 4]) != expected_crc:
            raise ValueError("PNG chunk checksum failed")
        # Never inflate client text/ICC/EXIF metadata. Keep only pixel chunks.
        if kind in {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS"}:
            sanitised.extend(data[offset:end])
        elif not kind[0] & 32:
            raise ValueError("Unsupported critical PNG chunk")
        if kind == b"IHDR" and offset != 8:
            raise ValueError("Duplicate PNG header")
        if offset == 8:
            if kind != b"IHDR" or length != 13:
                raise ValueError("Missing PNG dimensions")
            _dimensions(data[offset + 8 : offset + 16])
        if kind == b"IEND":
            ended = length == 0 and end == len(data)
            break
        offset = end
    if not ended:
        raise ValueError("Missing or invalid PNG end")
    return bytes(sanitised)


def _decode(encoded: str) -> Image.Image:
    try:
        data = _sanitise_png(base64.b64decode(encoded, validate=True))
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=["PNG"]) as source:
                source.verify()
            with Image.open(io.BytesIO(data), formats=["PNG"]) as source:
                source.load()
                # A fresh image discards EXIF, text, ICC and other client metadata.
                pixels = Image.new("RGB", source.size, "#080b12")
                if source.mode == "RGBA" or "transparency" in source.info:
                    rgba = source.convert("RGBA")
                    pixels.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    pixels.paste(source.convert("RGB"))
                return pixels
    except (
        ValueError,
        binascii.Error,
        OSError,
        SyntaxError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise InvalidRequest("Send one valid, bounded, non-animated PNG image.") from exc


def _json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


class SavedMapImageRenderer:
    def render(
        self,
        view: MapView,
        revision: MapViewRevision,
        options: MapImageOptions,
        received_at: datetime,
    ) -> bytes:
        credits = _attributions(revision.state.basemap, options)
        state = state_to_dict(revision.state)
        if not options.include_annotations:
            state.update(overlays=[], aoi=None)
            state.pop("measurement", None)
        metadata = {
            "view_id": str(view.id),
            "revision_id": str(revision.id),
            "revision_number": revision.number,
            "report_id": str(view.report_id),
            "report_version_id": str(revision.report_version_id),
            "report_version_number": revision.report_version_number,
            "saved_at": revision.created_at.isoformat(),
            "saved_revision_sha256": revision.content_sha256,
            "evidence_sha256": revision.evidence_sha256,
        }
        if options.include_annotations:
            credits.extend(item.attribution for item in revision.state.overlays if item.visible)
        image = _decode(options.png_base64)
        png = image_footer(
            image,
            [
                f"Report {view.report_id} / version {revision.report_version_number}",
                f"View {view.id} / revision {revision.id}",
                f"Server receipt {received_at.isoformat()} | {POLICY}",
                "Client-rendered pixels; correspondence and pixel redaction not verified.",
                "Saved private annotations included."
                if options.include_annotations
                else "Saved private annotations excluded; frozen evidence locations remain.",
                "Basemap current at export, not historical imagery.",
                "Legend: points are evidence locations; country-level positions are approximate.",
                "Unsupported geometry omitted. Flat maps omit geometry beyond +/-85.05112878 deg.",
                "Included saved annotations retain canonical geometry in map-state.json.",
                "Unsupported credit glyphs are represented by explicit Unicode code points.",
                *credits,
            ],
        )
        members = {
            "map.png": png,
            "map-state.json": _json(state),
            "revision.json": _json(metadata),
            "README.txt": (DISCLAIMER + "\n" + "\n".join(credits) + "\n").encode(),
        }
        manifest = {
            "schema_version": 1,
            "renderer_policy": POLICY,
            "server_received_at": received_at.isoformat(),
            "revision": metadata,
            "include_annotations": options.include_annotations,
            "use_basis": options.use_basis,
            "permitted_use": options.permitted_use,
            "attributions": credits,
            "overlay_attributions": [item.attribution for item in revision.state.overlays]
            if options.include_annotations
            else [],
            "disclosure": DISCLAIMER,
            "input_dimensions": [image.width, image.height],
            "output_dimensions": list(struct.unpack(">II", png[16:24])),
            "members": {
                name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                for name, data in members.items()
            },
        }
        members["manifest.json"] = _json(manifest)
        if sum(map(len, members.values())) > MAX_MAP_PACKAGE_BYTES:
            raise InvalidRequest("The map image package exceeds its 16 MiB uncompressed budget.")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in members.items():
                archive.writestr(name, data)
        return output.getvalue()
