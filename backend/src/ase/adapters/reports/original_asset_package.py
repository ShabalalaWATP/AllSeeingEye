"""Bounded offline original attachments with generated inert archive paths."""

import hashlib
import io
import json
import zipfile
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from ase.domain.errors import InvalidRequest
from ase.domain.original_assets import MAX_ASSET_BYTES, MAX_EXPORT_ASSET_BYTES, OriginalAssetContent
from ase.domain.report_records import ReportRecord, ReportVersion

MAX_PACKAGE_BYTES = 32 * 1024 * 1024


def _json(value: object) -> bytes:
    def convert(item: object) -> str:
        if isinstance(item, datetime):
            return item.isoformat()
        if isinstance(item, UUID):
            return str(item)
        raise TypeError("Unsupported original metadata")

    return (
        json.dumps(
            value,
            default=convert,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def render_original_package(
    record: ReportRecord,
    version: ReportVersion,
    base: bytes,
    selected: tuple[OriginalAssetContent, ...],
) -> bytes:
    if record.id != version.report_id or not 1 <= len(selected) <= 20:
        raise InvalidRequest("Invalid original asset selection.")
    if len({row.asset.id for row in selected}) != len(selected):
        raise InvalidRequest("Each original asset must be selected once.")
    if sum(len(row.content) for row in selected) > MAX_EXPORT_ASSET_BYTES:
        raise InvalidRequest("Selected originals exceed the 24 MiB limit.")
    for row in selected:
        asset = row.asset
        if (
            asset.report_id != record.id
            or asset.report_version_id != version.id
            or asset.version_number != version.number
            or asset.status != "active"
            or not 0 < len(row.content) <= MAX_ASSET_BYTES
            or asset.byte_count != len(row.content)
            or hashlib.sha256(row.content).hexdigest() != asset.sha256
        ):
            raise InvalidRequest("Selected originals do not match the frozen report version.")
    files: dict[str, bytes] = {}
    remaining = MAX_PACKAGE_BYTES

    def add(name: str, data: bytes) -> None:
        nonlocal remaining
        if len(data) > remaining:
            raise InvalidRequest("Selected original package exceeds the 32 MiB uncompressed limit.")
        if name in files:
            raise InvalidRequest("Duplicate package member.")
        remaining -= len(data)
        files[name] = data

    with zipfile.ZipFile(io.BytesIO(base)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "manifest.json" not in names:
            raise InvalidRequest("Invalid base evidence package.")
        base_manifest_name = (
            "annotations-manifest.json"
            if "original-manifest.json" in names
            else "original-manifest.json"
        )
        for entry in archive.infolist():
            if entry.file_size > remaining:
                raise InvalidRequest(
                    "Selected original package exceeds the 32 MiB uncompressed limit."
                )
            with archive.open(entry) as source:
                data = source.read(remaining + 1)
            add(base_manifest_name if entry.filename == "manifest.json" else entry.filename, data)
    metadata = []
    for row in selected:
        path = f"originals/{row.asset.id}.bin"
        add(path, row.content)
        exported_metadata = asdict(row.asset)
        exported_metadata.pop("session_family_id", None)
        metadata.append({**exported_metadata, "path": path})
    add(
        "original-assets.json",
        _json({"schema_version": "ase-selected-original-assets-v1", "assets": metadata}),
    )
    add(
        "ORIGINALS-README.txt",
        (
            b"Deliberately selected original attachments\n\n"
            b"Generated .bin paths are inert archive names. Source filenames are metadata only. "
            b"Hashes match retained bytes to frozen evidence; they do not establish authenticity, "
            b"truth, trusted time or permission to redistribute. Permitted-use text is an operator "
            b"declaration. Files can contain active or malicious content if opened externally. "
            b"Only explicitly selected originals are included. Earlier package members retain "
            b"their exact bytes, with their manifest renamed.\n"
        ),
    )
    add(
        "manifest.json",
        _json(
            {
                "schema_version": "ase-evidence-package-v4",
                "report_id": record.id,
                "version_id": version.id,
                "version": version.number,
                "base_package_sha256": hashlib.sha256(base).hexdigest(),
                "base_manifest": base_manifest_name,
                "original_assets_included": True,
                "selected_asset_ids": [row.asset.id for row in selected],
                "files": [
                    {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                    for name, data in files.items()
                ],
            }
        ),
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            entry = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o600 << 16
            archive.writestr(entry, data)
    return output.getvalue()
