"""Durable report work, with bounded frozen checkpoints and explicit lease state."""

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

ReportJobStatus = Literal["queued", "running", "paused", "completed", "needs_review", "failed"]
CheckpointStatus = Literal["running", "paused", "failed"]
MAX_JOB_PAYLOAD_BYTES = 2 * 1024 * 1024
MAX_JOB_SUMMARY_BYTES = 8192
MAX_JOB_LEASE_SECONDS = 3600
JOB_STATUSES = frozenset({"queued", "running", "paused", "completed", "needs_review", "failed"})
_CODE = re.compile(r"[a-z][a-z0-9_.:-]{0,119}\Z")
_SECRET_FIELDS = frozenset(
    {
        "api_key",
        "api_key_encrypted",
        "access_token",
        "refresh_token",
        "authorization",
        "password",
        "password_hash",
        "client_secret",
        "secret",
        "seed_events",
        "raw_events",
    }
)


def _check_scalar(value: Any) -> None:
    if type(value) is str:
        if len(value) > MAX_JOB_PAYLOAD_BYTES:
            raise ValueError("The report job checkpoint is too large.")
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError("Report job checkpoint numbers must be finite.")
    elif value is not None and type(value) not in (int, bool):
        raise ValueError("Report job checkpoints must contain JSON values only.")


def _check_json_tree(payload: dict[str, Any]) -> None:
    pending: list[tuple[Any, int]] = [(payload, 0)]
    nodes = 0
    while pending:
        value, depth = pending.pop()
        nodes += 1
        if depth > 40 or nodes > 200_000:
            raise ValueError("The report job checkpoint is too complex.")
        if type(value) is dict:
            if nodes + len(pending) + len(value) > 200_000:
                raise ValueError("The report job checkpoint is too complex.")
            for key, item in value.items():
                if type(key) is not str or key.casefold() in _SECRET_FIELDS:
                    raise ValueError("Report job checkpoints contain an unsupported field.")
                if len(key) > 200:
                    raise ValueError("The report job checkpoint field name is too long.")
                pending.append((item, depth + 1))
        elif type(value) in (list, tuple):
            if nodes + len(pending) + len(value) > 200_000:
                raise ValueError("The report job checkpoint is too complex.")
            pending.extend((item, depth + 1) for item in value)
        else:
            _check_scalar(value)


def canonical_job_payload(payload: dict[str, Any]) -> bytes:
    """Only bounded JSON is retained. Application code validates the typed stage schema."""
    if type(payload) is not dict or type(payload.get("schema_version")) is not int:
        raise ValueError("A report job needs a versioned JSON checkpoint.")
    if payload["schema_version"] != 1:
        raise ValueError("Unsupported report job checkpoint version.")
    _check_json_tree(payload)
    try:
        encoded = json.dumps(
            payload, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        summary = payload.get("summary", {})
        if (
            type(summary) is not dict
            or len(json.dumps(summary, ensure_ascii=False).encode("utf-8")) > MAX_JOB_SUMMARY_BYTES
        ):
            raise ValueError("The report job summary is invalid or too large.")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("The report job checkpoint cannot be encoded.") from exc
    if len(encoded) > MAX_JOB_PAYLOAD_BYTES:
        raise ValueError("The report job checkpoint is too large.")
    return encoded


def job_timestamp(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Report job timestamps must be timezone aware.")


def job_error(value: str | None) -> None:
    if value is not None and not _CODE.fullmatch(value):
        raise ValueError("Report job errors must be safe codes, not exception or source text.")


def job_stage(value: str) -> None:
    if not _CODE.fullmatch(value):
        raise ValueError("Use a short report job stage identifier.")


def job_lease(now: datetime, until: datetime) -> None:
    job_timestamp(now)
    job_timestamp(until)
    if not 0 < (until - now).total_seconds() <= MAX_JOB_LEASE_SECONDS:
        raise ValueError("Report job leases must last at most one hour.")


@dataclass(frozen=True, slots=True)
class ReportJob:
    id: UUID
    request_key: UUID
    owner_id: UUID
    team_id: UUID | None
    title: str
    status: ReportJobStatus
    stage: str
    created_at: datetime
    updated_at: datetime
    payload: dict[str, Any]
    report_id: UUID
    version_id: UUID
    revision: int = 1
    lease_token: UUID | None = None
    lease_until: datetime | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        if self.status not in JOB_STATUSES or type(self.revision) is not int or self.revision < 1:
            raise ValueError("Invalid report job status or revision.")
        if not 1 <= len(self.title.strip()) <= 300 or len(self.title) > 300:
            raise ValueError("Report job titles must contain at most 300 characters.")
        if any(ord(char) < 32 for char in self.title):
            raise ValueError("Report job titles contain unsupported control characters.")
        job_timestamp(self.created_at)
        job_timestamp(self.updated_at)
        if self.updated_at < self.created_at:
            raise ValueError("A report job cannot be updated before it was created.")
        job_stage(self.stage)
        job_error(self.error)
        if (self.lease_token is None) != (self.lease_until is None):
            raise ValueError("Report job leases require a token and expiry together.")
        if (self.status == "running") != (self.lease_token is not None):
            raise ValueError("Only running report jobs hold a lease.")
        if self.lease_until is not None:
            job_timestamp(self.lease_until)
        canonical_job_payload(self.payload)
