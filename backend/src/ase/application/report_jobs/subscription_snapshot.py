"""Bounded subscription comparison context for durable report snapshots.

The previous report's evidence remains in the authorised report repository. A job
stores only its exact reference and retained content digests, never a copied corpus.
"""

from dataclasses import replace
from typing import Any
from uuid import UUID

from ase.application.report_jobs.codec_boundary import count, identifier
from ase.application.reports.production_types import Job
from ase.application.reports.request import ReportRequest

MAX_SEEN_SIGNATURES = 500
_HEX = frozenset("0123456789abcdef")


def _signatures(value: Any) -> tuple[str, ...]:
    if type(value) is not list or len(value) > MAX_SEEN_SIGNATURES:
        raise ValueError("Invalid subscription content fingerprints")
    if any(type(item) is not str or len(item) != 64 or not set(item) <= _HEX for item in value):
        raise ValueError("Invalid subscription content fingerprint")
    if len(set(value)) != len(value):
        raise ValueError("Duplicate subscription content fingerprint")
    return tuple(value)


def freeze_subscription_context(job: Job) -> dict[str, Any] | None:
    request = job.request
    if request.subscription_previous_report_id is None and not request.subscription_seen_signatures:
        return None
    if not request.automation:
        raise ValueError("Subscription context requires an automated report")
    baseline = job.subscription_baseline
    if baseline is not None and baseline.report_id != request.subscription_previous_report_id:
        raise ValueError("The subscription baseline reference changed")
    version = baseline.number if baseline is not None else None
    if baseline is not None and (
        job.scope.get("subscription_previous_report_id") != str(baseline.report_id)
        or job.scope.get("subscription_previous_version") != version
    ):
        raise ValueError("The subscription baseline is not pinned in the saved scope")
    seen = list(request.subscription_seen_signatures)
    _signatures(seen)
    return {
        "report_id": str(request.subscription_previous_report_id)
        if request.subscription_previous_report_id is not None
        else None,
        "version": version,
        "seen_signatures": seen,
    }


def restore_subscription_context(
    value: Any, request: ReportRequest, scope: dict[str, Any]
) -> ReportRequest:
    if type(value) is not dict or set(value) != {
        "report_id",
        "version",
        "seen_signatures",
    }:
        raise ValueError("Invalid subscription snapshot fields")
    report_id: UUID | None = identifier(value["report_id"])
    version = value["version"]
    if version is not None:
        count(version)
        if version < 1 or report_id is None:
            raise ValueError("Invalid subscription baseline version")
    if not request.automation:
        raise ValueError("Subscription context requires an automated report")
    if version is None:
        if "subscription_previous_report_id" in scope or "subscription_previous_version" in scope:
            raise ValueError("Unpinned subscription baseline")
    elif (
        scope.get("subscription_previous_report_id") != str(report_id)
        or scope.get("subscription_previous_version") != version
    ):
        raise ValueError("The subscription baseline reference changed")
    seen = _signatures(value["seen_signatures"])
    if report_id is None and not seen:
        raise ValueError("Empty subscription context")
    return replace(
        request,
        subscription_previous_report_id=report_id,
        subscription_seen_signatures=seen,
    )
