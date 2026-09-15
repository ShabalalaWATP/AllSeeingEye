"""Lossless codecs for frozen subscription ledger rows."""

from __future__ import annotations

from datetime import datetime

from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionAttemptRow,
    SubscriptionDeliveryRow,
    SubscriptionEditionRow,
    SubscriptionLineageRow,
    SubscriptionRevisionRow,
)
from ase.domain.subscription_editions import (
    EditionAttempt,
    EditionCoverage,
    EditionDelivery,
    EditionQuality,
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
    SubscriptionLineage,
    SubscriptionRevision,
)


def _intervals_to_json(values: tuple[ObservationInterval, ...]) -> list[dict[str, str]]:
    return [{"start": item.start.isoformat(), "end": item.end.isoformat()} for item in values]


def _intervals_from_json(values: list[dict[str, str]]) -> tuple[ObservationInterval, ...]:
    return tuple(
        ObservationInterval(
            datetime.fromisoformat(item["start"]), datetime.fromisoformat(item["end"])
        )
        for item in values
    )


def revision_values(value: SubscriptionRevision) -> dict[str, object]:
    return {
        "subscription_id": value.subscription_id,
        "revision": value.revision,
        "owner_id": value.owner_id,
        "team_id": value.team_id,
        "request_snapshot": value.request_snapshot,
        "compatibility_fingerprint": value.compatibility_fingerprint,
        "recurrence_policy": value.recurrence_policy,
        "collection_policy": value.collection_policy,
        "enabled": value.enabled,
        "created_at": value.created_at,
        "brief_revision_id": value.brief_revision_id,
    }


def revision_from_row(row: SubscriptionRevisionRow) -> SubscriptionRevision:
    return SubscriptionRevision(
        subscription_id=row.subscription_id,
        revision=row.revision,
        owner_id=row.owner_id,
        team_id=row.team_id,
        request_snapshot=row.request_snapshot,
        compatibility_fingerprint=row.compatibility_fingerprint,
        recurrence_policy=row.recurrence_policy,
        collection_policy=row.collection_policy,
        enabled=row.enabled,
        created_at=row.created_at,
        brief_revision_id=row.brief_revision_id,
    )


def edition_values(value: SubscriptionEdition) -> dict[str, object]:
    return {
        "id": value.id,
        "subscription_id": value.subscription_id,
        "trigger": value.trigger.value,
        "due_at_utc": value.due_at_utc,
        "request_uuid": value.request_uuid,
        "frozen_revision": value.frozen_revision,
        "requested_start": value.requested.start,
        "requested_end": value.requested.end,
        "effective_intervals": _intervals_to_json(value.effective_intervals),
        "gaps": _intervals_to_json(value.gaps),
        "compatibility_fingerprint": value.compatibility_fingerprint,
        "baseline_version_id": value.baseline_version_id,
        "workflow": value.workflow.value,
        "report_quality": value.report_quality.value,
        "coverage": value.coverage.value,
        "created_at": value.created_at,
        "updated_at": value.updated_at,
        "revision": value.revision,
        "job_id": value.job_id,
        "report_id": value.report_id,
        "version_id": value.version_id,
        "safe_reason": value.safe_reason,
        "covered_by_edition_id": value.covered_by_edition_id,
        "accepted_as_baseline": value.accepted_as_baseline,
    }


def edition_from_row(row: SubscriptionEditionRow) -> SubscriptionEdition:
    return SubscriptionEdition(
        id=row.id,
        subscription_id=row.subscription_id,
        trigger=EditionTrigger(row.trigger),
        due_at_utc=row.due_at_utc,
        request_uuid=row.request_uuid,
        frozen_revision=row.frozen_revision,
        requested=ObservationInterval(row.requested_start, row.requested_end),
        effective_intervals=_intervals_from_json(row.effective_intervals),
        gaps=_intervals_from_json(row.gaps),
        compatibility_fingerprint=row.compatibility_fingerprint,
        baseline_version_id=row.baseline_version_id,
        workflow=EditionWorkflow(row.workflow),
        report_quality=EditionQuality(row.report_quality),
        coverage=EditionCoverage(row.coverage),
        created_at=row.created_at,
        updated_at=row.updated_at,
        revision=row.revision,
        job_id=row.job_id,
        report_id=row.report_id,
        version_id=row.version_id,
        safe_reason=row.safe_reason,
        covered_by_edition_id=row.covered_by_edition_id,
        accepted_as_baseline=row.accepted_as_baseline,
    )


def lineage_values(value: SubscriptionLineage) -> dict[str, object]:
    return {
        "subscription_id": value.subscription_id,
        "compatibility_fingerprint": value.compatibility_fingerprint,
        "analytical_baseline_version_id": value.analytical_baseline_version_id,
        "covered_intervals": _intervals_to_json(value.covered_intervals),
        "complete_cutoff": value.complete_cutoff,
        "updated_at": value.updated_at,
        "revision": value.revision,
    }


def lineage_from_row(row: SubscriptionLineageRow) -> SubscriptionLineage:
    return SubscriptionLineage(
        subscription_id=row.subscription_id,
        compatibility_fingerprint=row.compatibility_fingerprint,
        analytical_baseline_version_id=row.analytical_baseline_version_id,
        covered_intervals=_intervals_from_json(row.covered_intervals),
        complete_cutoff=row.complete_cutoff,
        updated_at=row.updated_at,
        revision=row.revision,
    )


def attempt_values(value: EditionAttempt) -> dict[str, object]:
    return {
        "id": value.id,
        "edition_id": value.edition_id,
        "job_id": value.job_id,
        "number": value.number,
        "stage": value.stage,
        "started_at": value.started_at,
        "ended_at": value.ended_at,
        "outcome": value.outcome,
        "next_retry_at": value.next_retry_at,
        "lease_token": value.lease_token,
        "job_revision": value.job_revision,
        "reserved_requests": value.reserved_requests,
        "actual_requests": value.actual_requests,
        "reserved_output_tokens": value.reserved_output_tokens,
        "actual_output_tokens": value.actual_output_tokens,
    }


def attempt_from_row(row: SubscriptionAttemptRow) -> EditionAttempt:
    return EditionAttempt(
        id=row.id,
        edition_id=row.edition_id,
        job_id=row.job_id,
        number=row.number,
        stage=row.stage,
        started_at=row.started_at,
        ended_at=row.ended_at,
        outcome=row.outcome,
        next_retry_at=row.next_retry_at,
        lease_token=row.lease_token,
        job_revision=row.job_revision,
        reserved_requests=row.reserved_requests,
        actual_requests=row.actual_requests,
        reserved_output_tokens=row.reserved_output_tokens,
        actual_output_tokens=row.actual_output_tokens,
    )


def delivery_values(value: EditionDelivery) -> dict[str, object]:
    return {
        "id": value.id,
        "edition_id": value.edition_id,
        "channel": value.channel,
        "destination_ref": value.destination_ref,
        "event_kind": value.event_kind,
        "idempotency_key": value.idempotency_key,
        "state": value.state,
        "attempts": value.attempts,
        "created_at": value.created_at,
        "updated_at": value.updated_at,
    }


def delivery_from_row(row: SubscriptionDeliveryRow) -> EditionDelivery:
    return EditionDelivery(
        id=row.id,
        edition_id=row.edition_id,
        channel=row.channel,
        destination_ref=row.destination_ref,
        event_kind=row.event_kind,
        idempotency_key=row.idempotency_key,
        state=row.state,
        attempts=row.attempts,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
