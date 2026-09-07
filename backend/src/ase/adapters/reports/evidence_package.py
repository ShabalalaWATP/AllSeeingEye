"""Deterministic bounded packages of already-frozen evidence, without network access."""

import hashlib
import io
import json
import math
import zipfile
from datetime import datetime
from typing import Any
from uuid import UUID

from ase.domain.errors import InvalidRequest
from ase.domain.observation import observation_to_dict
from ase.domain.project import project_to_dict
from ase.domain.report_records import (
    ReportRecord,
    ReportVersion,
    analysis_to_dict,
    body_to_dict,
    evidence_to_list,
)

MAX_PACKAGE_BYTES = 8 * 1024 * 1024
MAX_EVIDENCE = 1000


def _json(value: object, remaining: int = MAX_PACKAGE_BYTES) -> bytes:
    def convert(item: object) -> str:
        if isinstance(item, datetime | UUID):
            return str(item)
        raise TypeError("Unsupported package value")

    encoder = json.JSONEncoder(
        default=convert, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
    )
    output = io.BytesIO()
    for part in encoder.iterencode(value):
        encoded = part.encode("utf-8")
        if output.tell() + len(encoded) + 1 > remaining:
            raise InvalidRequest("Evidence package exceeds the 8 MiB uncompressed limit.")
        output.write(encoded)
    output.write(b"\n")
    return output.getvalue()


def evidence_geojson(version: ReportVersion) -> dict[str, Any]:
    """Unlocated findings remain null geometries; never export centroid incident points."""
    features: list[dict[str, Any]] = []
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
                    "published_at": item.published_at.isoformat() if item.published_at else None,
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
        if item.geometry is not None:
            geometry = item.geometry
            feature = features[-1]
            feature["geometry"] = geometry.to_geometry()
            feature["properties"].update(
                {
                    "location_role": geometry.location_role.value,
                    "precision": geometry.precision,
                    "geometry_sha256": geometry.sha256,
                    "geometry_method": geometry.method,
                    "geometry_source_id": geometry.source_id,
                    "geometry_attribution": geometry.attribution,
                    "notice": "Original source geometry; structural validation does not establish "
                    "topological validity, an incident or usable sensor coverage.",
                }
            )
        if item.project is not None:
            features[-1]["properties"]["project"] = project_to_dict(item.project)
        if item.observation is not None:
            features[-1]["properties"]["observation"] = observation_to_dict(item.observation)
    return {"type": "FeatureCollection", "features": features}


class FrozenEvidencePackageRenderer:
    def render(self, record: ReportRecord, version: ReportVersion) -> bytes:
        if version.report_id != record.id or len(version.evidence) > MAX_EVIDENCE:
            raise InvalidRequest("Invalid or oversized evidence package.")
        # Reject excessive source geometry before materialising its JSON trees.
        # Coordinates occur in evidence.json and evidence.geojson. This lower-bound
        # check is followed by incremental encoding under the remaining byte budget.
        minimum = len(version.markdown.encode("utf-8"))
        for item in version.evidence:
            if item.geometry is not None:
                minimum += 2 * len(item.geometry.source_geometry.encode("utf-8"))
            minimum += len(item.title.encode("utf-8")) + len((item.summary or "").encode("utf-8"))
            if minimum > MAX_PACKAGE_BYTES:
                raise InvalidRequest("Evidence package exceeds the 8 MiB uncompressed limit.")
        files: dict[str, bytes] = {}
        remaining = MAX_PACKAGE_BYTES

        def add(name: str, value: object) -> None:
            nonlocal remaining
            content = value if isinstance(value, bytes) else _json(value, remaining)
            if len(content) > remaining:
                raise InvalidRequest("Evidence package exceeds the 8 MiB uncompressed limit.")
            remaining -= len(content)
            files[name] = content

        add("report.md", version.markdown.encode("utf-8"))
        add(
            "report.json",
            {
                "report_id": record.id,
                "version_id": version.id,
                "version": version.number,
                "body": body_to_dict(version.body),
            },
        )
        add("evidence.json", evidence_to_list(version.evidence))
        add("analysis.json", analysis_to_dict(version))
        add("evidence.geojson", evidence_geojson(version))
        add(
            "README.txt",
            (
                b"Frozen research evidence package\n\n"
                b"Contains the saved report, captured excerpts, citation locators, source URLs, "
                b"source assessments, collection receipts and retained source geometry. "
                b"No source URLs were fetched during export. Original pages, media, documents "
                b"and external map tiles are not included. "
                b"Missing legacy metadata remains unknown.\n\n"
                b"File SHA-256 digests check package integrity, not source authenticity. Existing "
                b"evidence content hashes describe captured content, "
                b"not necessarily original files. "
                b"No signature or trusted timestamp is supplied. Source rights still apply; "
                b"this package does not grant permission to republish captured excerpts.\n"
            ),
        )
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
        add("manifest.json", manifest)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                archive.writestr(info, content)
        return output.getvalue()
