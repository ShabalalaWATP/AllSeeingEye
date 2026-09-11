"""Request identity and explicit resume transitions, without losing paid reservations."""

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from ase.application.ports.report_jobs import ReportJobRepository
from ase.application.report_jobs.budget import MAX_CALLS, MAX_OUTPUT_TOKENS, output_used
from ase.application.reports.request import ReportRequest
from ase.domain.errors import Conflict, InvalidRequest, RateLimited
from ase.domain.report_jobs import ReportJob

NON_RESUMABLE_ERRORS = frozenset(
    {
        "budget_exhausted",
        "report_job_budget_exhausted",
        "profile_changed",
        "model_changed",
        "routing_changed",
        "template_changed",
        "invalid_snapshot",
        "invalid_packet",
        "section_token_budget_exhausted",
    }
)
MAX_ACTIVE_PER_OWNER = 2
MAX_OPEN_PER_OWNER = 20
MAX_OPEN_GLOBAL = 100


async def require_capacity(repo: ReportJobRepository, owner_id: UUID, *, creating: bool) -> None:
    """The caller holds the shared administration lock across this count and admission."""
    if await repo.count_active(owner_id) >= MAX_ACTIVE_PER_OWNER:
        raise RateLimited(60)
    if creating and (
        await repo.count_open(owner_id) >= MAX_OPEN_PER_OWNER
        or await repo.count_open() >= MAX_OPEN_GLOBAL
    ):
        raise InvalidRequest(
            "The retained report-job limit has been reached. Complete existing work first."
        )


def _scalar(value: Any) -> str:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    raise TypeError("Unsupported request identity value")


def request_digest(request: ReportRequest) -> str:
    """Hash the original request, including private input identity, without retaining it."""
    try:
        value = json.dumps(
            asdict(request),
            default=_scalar,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise InvalidRequest("The report request could not be identified safely.") from None
    if len(value) > 1024 * 1024:
        raise InvalidRequest("The report request exceeds its size limit.")
    return hashlib.sha256(value).hexdigest()


def require_same_request(job: ReportJob, digest: str) -> None:
    if job.payload.get("request_digest") != digest:
        raise Conflict("This request identifier was already used for a different report.")


def has_budget(payload: dict[str, Any]) -> bool:
    calls = payload.get("calls", [])
    return (
        isinstance(calls, list)
        and len(calls) < MAX_CALLS
        and output_used(payload) < MAX_OUTPUT_TOKENS
    )


def resumed_payload(job: ReportJob) -> dict[str, Any]:
    """Only an explicit resume permits retrying an interrupted section.

    The previous call stays uncertain and consumes its full reservation. Completed
    sections and exhausted request hashes remain unchanged, preventing free replays.
    """
    if job.error in NON_RESUMABLE_ERRORS or not has_budget(job.payload):
        raise InvalidRequest("This report cannot resume with its saved settings or allowance.")
    payload = deepcopy(job.payload)
    for call in payload.get("calls", []):
        if call.get("status") == "in_flight":
            call["status"] = "uncertain"
            call["error"] = "interrupted"
    packet = payload.get("current_packet")
    sections = payload.get("sections", {})
    if type(sections) is not dict:
        raise InvalidRequest("The report section checkpoint is unavailable.")
    for key, section in sections.items():
        if (
            type(section) is dict
            and packet is not None
            and section.get("packet_digest") == packet
            and key == f"{packet}:{section.get('section_id')}"
            and section.get("status") == "running"
        ):
            section["status"] = "incomplete"
            section["reason"] = "interrupted"
    return payload
