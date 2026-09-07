"""Offline v2 packages preserve base evidence bytes and explicitly selected revisions."""

import hashlib
import io
import json
import zipfile
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from ase.adapters.reports.evidence_package import MAX_PACKAGE_BYTES, FrozenEvidencePackageRenderer
from ase.adapters.reports.identity_package_validation import validate_identity_selection
from ase.domain.claim_revisions import (
    ClaimCitationInput,
    ClaimRevision,
    freeze_claim_citations,
    validate_claim_revision,
)
from ase.domain.errors import InvalidRequest
from ase.domain.identity_review import IdentityDecisionRevision
from ase.domain.report_records import ReportRecord, ReportVersion

MAX_SELECTED_REVISIONS = 20
BASE_FILES = frozenset(
    {
        "report.md",
        "report.json",
        "evidence.json",
        "analysis.json",
        "evidence.geojson",
        "README.txt",
        "manifest.json",
    }
)


def _json(value: object) -> bytes:
    def convert(item: object) -> str:
        if isinstance(item, datetime):
            return item.isoformat()
        if isinstance(item, UUID):
            return str(item)
        raise TypeError("Unsupported claim package value")

    output = io.BytesIO()
    encoder = json.JSONEncoder(
        default=convert, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )
    for chunk in encoder.iterencode(value):
        encoded = chunk.encode("utf-8")
        if output.tell() + len(encoded) + 1 > MAX_PACKAGE_BYTES:
            raise InvalidRequest("Selected claim package exceeds the 8 MiB uncompressed limit.")
        output.write(encoded)
    output.write(b"\n")
    return output.getvalue()


def _validate(version: ReportVersion, revisions: tuple[ClaimRevision, ...]) -> None:
    if not 1 <= len(revisions) <= MAX_SELECTED_REVISIONS:
        raise InvalidRequest("Select between one and twenty exact claim revisions.")
    if len({row.id for row in revisions}) != len(revisions):
        raise InvalidRequest("A claim revision can only be selected once.")
    for row in revisions:
        try:
            validate_claim_revision(row)
            if row.report_id != version.report_id or row.report_version_id != version.id:
                raise ValueError("Selected revision belongs to another frozen report version")
            inputs = tuple(
                ClaimCitationInput(
                    item.label,
                    item.relation,
                    item.excerpt.field,
                    item.excerpt.start,
                    item.excerpt.end,
                    item.excerpt.text,
                )
                for item in row.citations
            )
            if freeze_claim_citations(version, inputs) != row.citations:
                raise ValueError("Selected citation differs from frozen evidence")
        except ValueError as exc:
            raise InvalidRequest(
                "Selected claims do not match the frozen report evidence."
            ) from exc


class SelectedClaimPackageRenderer:
    """Caller authorises every selected revision and rechecks access after rendering.

    No source URLs are fetched. Earlier report files and the v1 manifest retain
    their exact contents; this new container has its own manifest and integrity hash.
    """

    def render(
        self,
        record: ReportRecord,
        version: ReportVersion,
        revisions: tuple[ClaimRevision, ...],
        *,
        identity_revisions: tuple[IdentityDecisionRevision, ...] = (),
    ) -> bytes:
        if record.id != version.report_id:
            raise InvalidRequest("The report and version do not match.")
        if not 1 <= len(revisions) + len(identity_revisions) <= MAX_SELECTED_REVISIONS:
            raise InvalidRequest("Select between one and twenty exact annotation revisions.")
        if revisions:
            _validate(version, revisions)
        validate_identity_selection(record, version, identity_revisions)
        base = FrozenEvidencePackageRenderer().render(record, version)
        files: dict[str, bytes] = {}
        remaining = MAX_PACKAGE_BYTES

        def add(name: str, content: bytes) -> None:
            nonlocal remaining
            if len(content) > remaining:
                raise InvalidRequest("Selected claim package exceeds the 8 MiB uncompressed limit.")
            remaining -= len(content)
            files[name] = content

        with zipfile.ZipFile(io.BytesIO(base)) as archive:
            if set(archive.namelist()) != BASE_FILES or len(archive.infolist()) != len(BASE_FILES):
                raise InvalidRequest("Unexpected base evidence package structure.")
            for entry in archive.infolist():
                if entry.file_size > remaining:
                    raise InvalidRequest(
                        "Selected claim package exceeds the 8 MiB uncompressed limit."
                    )
                with archive.open(entry) as source:
                    content = source.read(remaining + 1)
                add(
                    "original-manifest.json"
                    if entry.filename == "manifest.json"
                    else entry.filename,
                    content,
                )
        add(
            "claim-revisions.json",
            _json(
                {
                    "schema_version": "ase-selected-claim-revisions-v1",
                    "report_id": record.id,
                    "report_version_id": version.id,
                    "selection": "Explicit exact revisions; unselected history is not included.",
                    "revisions": [asdict(row) for row in revisions],
                }
            ),
        )
        add(
            "CLAIMS-README.txt",
            (
                b"Selected claim revisions\n\n"
                b"These annotations are anchored to the frozen report version. Proposed, reviewed "
                b"and withdrawn describe review history, not truth or source reliability. Original "
                b"excerpts establish literal presence, not semantic support. Corrections preserve "
                b"the report and its original grades. Only selected revisions are included.\n\n"
                b"Original report files and original-manifest.json retain their original bytes. "
                b"manifest.json describes this new package. Hashes verify exported content, not "
                b"authenticity, trusted time or permission to redistribute source material.\n"
            ),
        )
        if identity_revisions:
            add(
                "identity-revisions.json",
                _json(
                    {
                        "schema_version": "ase-selected-identity-revisions-v1",
                        "report_id": record.id,
                        "report_version_id": version.id,
                        "selection": (
                            "Explicit exact revisions; unselected history is not included."
                        ),
                        "revisions": [asdict(row) for row in identity_revisions],
                    }
                ),
            )
            add(
                "IDENTITIES-README.txt",
                b"Selected operator identity reviews\n\n"
                b"Matched, rejected, unresolved and withdrawn are attributed operator decisions. "
                b"They do not authenticate registry assertions, establish ownership, merge "
                b"identities or change source grades. Identifiers and jurisdiction assertions "
                b"retain their captured namespaces and text. Only selected revisions are included; "
                b"a predecessor ID does not mean its revision is included.\n",
            )
        add(
            "manifest.json",
            _json(
                {
                    "schema_version": "ase-evidence-package-v3"
                    if identity_revisions
                    else "ase-evidence-package-v2",
                    "report_id": str(record.id),
                    "version_id": str(version.id),
                    "version": version.number,
                    "base_package_sha256": hashlib.sha256(base).hexdigest(),
                    "original_manifest": "original-manifest.json",
                    "selected_revision_ids": [str(row.id) for row in revisions],
                    **(
                        {
                            "selected_identity_revision_ids": [
                                str(row.id) for row in identity_revisions
                            ]
                        }
                        if identity_revisions
                        else {}
                    ),
                    "original_assets_included": False,
                    "files": [
                        {
                            "path": name,
                            "bytes": len(content),
                            "sha256": hashlib.sha256(content).hexdigest(),
                        }
                        for name, content in files.items()
                    ],
                }
            ),
        )
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                entry = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o600 << 16
                archive.writestr(entry, content)
        return output.getvalue()
