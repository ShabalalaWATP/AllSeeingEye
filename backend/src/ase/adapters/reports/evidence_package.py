"""Deterministic bounded packages of already-frozen evidence, without network access."""

import hashlib
import io
import json
import math
import zipfile
from dataclasses import asdict
from datetime import datetime
from typing import Any
from uuid import UUID

from ase.domain.errors import InvalidRequest
from ase.domain.report_records import ReportRecord, ReportVersion, analysis_to_dict, body_to_dict

MAX_PACKAGE_BYTES = 8 * 1024 * 1024
MAX_EVIDENCE = 1000


def _json(value: object) -> bytes:
    def convert(item: object) -> str:
        if isinstance(item, datetime | UUID):
            return str(item)
        raise TypeError("Unsupported package value")

    return (
        json.dumps(
            value, default=convert, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def evidence_geojson(version: ReportVersion) -> dict[str, Any]:
    """Unlocated findings remain null geometries; never export centroid incident points."""
    features = []
    for item in version.evidence:
        located = (
            item.geo_confidence in {"exact", "city", "admin1"}
            and item.lon is not None
            and item.lat is not None
            and math.isfinite(item.lon)
            and math.isfinite(item.lat)
            and -180 <= item.lon <= 180
            and -90 <= item.lat <= 90
        )
        features.append(
            {
                "type": "Feature",
                "id": f"{version.id}:{item.label}",
                "geometry": {"type": "Point", "coordinates": [item.lon, item.lat]}
                if located
                else None,
                "properties": {
                    "evidence_label": item.label,
                    "source_id": item.source_id,
                    "title": item.title,
                    "precision": item.geo_confidence,
                    "country_iso": item.country_iso,
                    "published_at": item.published_at.isoformat(),
                    "captured_at": item.captured_at.isoformat(),
                    "location_role": "unknown",
                    "notice": (
                        "Frozen source location; incident role is not established. "
                        "Approximate points are not exact coordinates."
                    )
                    if located
                    else "No supported point geometry; country context is not an incident site.",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


class FrozenEvidencePackageRenderer:
    def render(self, record: ReportRecord, version: ReportVersion) -> bytes:
        if version.report_id != record.id or len(version.evidence) > MAX_EVIDENCE:
            raise InvalidRequest("Invalid or oversized evidence package.")
        files = {
            "report.md": version.markdown.encode("utf-8"),
            "report.json": _json(
                {
                    "report_id": record.id,
                    "version_id": version.id,
                    "version": version.number,
                    "body": body_to_dict(version.body),
                }
            ),
            "evidence.json": _json([asdict(item) for item in version.evidence]),
            "analysis.json": _json(analysis_to_dict(version)),
            "evidence.geojson": _json(evidence_geojson(version)),
            "README.txt": (
                b"Frozen research evidence package\n\n"
                b"Contains the saved report, captured excerpts, citation locators, source URLs, "
                b"source assessments, collection receipts and supported point geometry. "
                b"No source URLs were fetched during export. Original pages, media, documents "
                b"and external map tiles are not included. "
                b"Missing legacy metadata remains unknown.\n\n"
                b"File SHA-256 digests check package integrity, not source authenticity. Existing "
                b"evidence content hashes describe captured content, "
                b"not necessarily original files. "
                b"No signature or trusted timestamp is supplied. Source rights still apply; "
                b"this package does not grant permission to republish captured excerpts.\n"
            ),
        }
        manifest = {
            "schema_version": "ase-evidence-package-v1",
            "report_id": str(record.id),
            "version_id": str(version.id),
            "version": version.number,
            "created_at": version.created_at.isoformat(),
            "evidence_count": len(version.evidence),
            "original_assets_included": False,
            "licence": (
                "Source-specific rights apply; redistribution permission is not established."
            ),
            "files": [
                {"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                for name, content in files.items()
            ],
        }
        files["manifest.json"] = _json(manifest)
        if sum(map(len, files.values())) > MAX_PACKAGE_BYTES:
            raise InvalidRequest("Evidence package exceeds the 8 MiB uncompressed limit.")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                archive.writestr(info, content)
        return output.getvalue()
