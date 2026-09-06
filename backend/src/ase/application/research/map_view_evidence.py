"""Bind saved views to map-relevant frozen evidence, excluding later archive links."""

import hashlib
import json

from ase.domain.errors import InvalidRequest
from ase.domain.map_views import MapViewState
from ase.domain.report_records import ReportVersion, evidence_to_list


def evidence_digest(version: ReportVersion) -> str:
    rows = evidence_to_list(version.evidence)
    for row in rows:
        row.pop("archive_url", None)
    encoded = json.dumps(
        rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_selection(state: MapViewState, version: ReportVersion) -> None:
    if state.selected_evidence is not None and state.selected_evidence not in {
        item.label for item in version.evidence
    }:
        raise InvalidRequest("Selected evidence is absent from this report version.")
    if not set(state.source_ids).issubset({item.source_id for item in version.evidence}):
        raise InvalidRequest("Map source filters must refer to this report version.")
