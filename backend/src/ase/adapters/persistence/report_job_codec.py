"""Verify bounded checkpoint integrity before reconstructing a durable job."""

import hashlib
import json
from typing import Any, cast

from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.domain.errors import Conflict
from ase.domain.report_jobs import (
    MAX_JOB_PAYLOAD_BYTES,
    ReportJob,
    ReportJobStatus,
    canonical_job_payload,
)


def payload_columns(payload: dict[str, Any]) -> dict[str, Any]:
    encoded = canonical_job_payload(payload)
    return {
        "payload": encoded.decode("utf-8"),
        "payload_sha256": hashlib.sha256(encoded).hexdigest(),
        "payload_bytes": len(encoded),
    }


def with_payload(row: ReportJobRow, payload: dict[str, Any]) -> ReportJob:
    return ReportJob(
        id=row.id,
        request_key=row.request_key,
        owner_id=row.owner_id,
        team_id=row.team_id,
        title=row.title,
        status=cast(ReportJobStatus, row.status),
        stage=row.stage,
        created_at=row.created_at,
        updated_at=row.updated_at,
        payload=payload,
        report_id=row.report_id,
        version_id=row.version_id,
        revision=row.revision,
        lease_token=row.lease_token,
        lease_until=row.lease_until,
        error=row.error,
    )


def from_row(row: ReportJobRow) -> ReportJob:
    try:
        if (
            not 2 <= row.payload_bytes <= MAX_JOB_PAYLOAD_BYTES
            or len(row.payload) > row.payload_bytes
        ):
            raise ValueError("Invalid payload size")
        encoded = row.payload.encode("utf-8")
        if (
            len(encoded) != row.payload_bytes
            or hashlib.sha256(encoded).hexdigest() != row.payload_sha256
        ):
            raise ValueError("Invalid payload integrity")
        payload = json.loads(encoded)
        if canonical_job_payload(payload) != encoded:
            raise ValueError("Invalid checkpoint encoding")
        return with_payload(row, payload)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise Conflict(
            "The retained report job checkpoint is unavailable or inconsistent."
        ) from exc
