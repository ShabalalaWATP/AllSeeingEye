"""Bounded content anchors for mutable report objects supplied to offline rendering."""

import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from uuid import UUID

from ase.domain.errors import InvalidRequest
from ase.domain.report_records import ReportRecord, ReportVersion


def export_content_digest(record: ReportRecord, version: ReportVersion) -> str:
    def convert(value: object) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, Enum):
            return str(value.value)
        raise TypeError("Unsupported report content")

    # Include every supplied field, even metadata currently omitted by the renderer.
    # This guards future renderer additions without weakening existing anchors.
    encoder = json.JSONEncoder(default=convert, sort_keys=True, ensure_ascii=False, allow_nan=False)
    digest = hashlib.sha256()
    size = 0
    try:
        for part in encoder.iterencode({"record": asdict(record), "version": asdict(version)}):
            encoded = part.encode("utf-8")
            size += len(encoded)
            if size > 16 * 1024 * 1024:
                raise InvalidRequest("Report content exceeds the export admission limit.")
            digest.update(encoded)
    except (TypeError, ValueError, RecursionError) as exc:
        raise InvalidRequest("Report content cannot be safely exported.") from exc
    return digest.hexdigest()
