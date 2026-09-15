"""Bounded, authorised subscription edition history projections."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ase.domain.research_changes import ComparisonReason, ComparisonState
from ase.domain.subscription_comparisons import EditionComparison
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionDelivery,
    EditionQuality,
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
    SubscriptionLineage,
)


class ObservationIntervalOut(BaseModel):
    start: datetime
    end: datetime

    @classmethod
    def from_interval(cls, interval: ObservationInterval) -> "ObservationIntervalOut":
        return cls(start=interval.start, end=interval.end)


class RunNowIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID


class EditionComparisonOut(BaseModel):
    previous_version_id: UUID | None
    current_version_id: UUID
    state: ComparisonState
    reasons: list[ComparisonReason]
    changed_claims: int
    corrected_evidence: int
    novel_evidence: int
    syndicated_duplicates: int
    summary: str

    @classmethod
    def from_comparison(cls, value: EditionComparison) -> "EditionComparisonOut":
        result = value.result
        summaries = {
            ComparisonState.FAILURE: "Comparison unavailable because this edition failed.",
            ComparisonState.INSUFFICIENT_COVERAGE: (
                "Coverage or the compatible baseline was insufficient for a quiet-period claim."
            ),
            ComparisonState.SIGNIFICANT_CONTRADICTION_OR_CORRECTION: (
                "Captured evidence includes an explicit correction or significant contradiction."
            ),
            ComparisonState.ASSESSMENT_CHANGED: "The assessment changed between exact versions.",
            ComparisonState.NEW_EVIDENCE_UNCHANGED_ASSESSMENT: (
                "New captured evidence did not change the recorded assessment."
            ),
            ComparisonState.NO_NEW_RELEVANT_EVIDENCE: (
                "No new relevant evidence was captured with adequate recorded coverage."
            ),
        }
        summary = summaries[result.state]
        if (
            result.state is ComparisonState.INSUFFICIENT_COVERAGE
            and ComparisonReason.CLAIM_MAPPING_UNRESOLVED in result.reasons
        ):
            summary = (
                "Claim mapping between saved editions is unresolved and needs review "
                "before declaring an assessment change or quiet interval."
            )
        return cls(
            previous_version_id=value.previous_version_id,
            current_version_id=value.current_version_id,
            state=result.state,
            reasons=list(result.reasons),
            changed_claims=len(result.changed_claim_ids),
            corrected_evidence=len(result.corrected_evidence_ids),
            novel_evidence=len(result.novel_evidence_ids),
            syndicated_duplicates=len(result.syndicated_duplicate_ids),
            summary=summary,
        )


class SubscriptionEditionOut(BaseModel):
    id: UUID
    subscription_id: UUID
    trigger: EditionTrigger
    due_at_utc: datetime | None
    frozen_revision: int
    requested: ObservationIntervalOut
    effective_intervals: list[ObservationIntervalOut]
    gaps: list[ObservationIntervalOut]
    workflow: EditionWorkflow
    report_quality: EditionQuality
    coverage: EditionCoverage
    job_id: UUID | None
    report_id: UUID | None
    version_id: UUID | None
    covered_by_edition_id: UUID | None
    accepted_as_baseline: bool
    safe_reason: str | None
    created_at: datetime
    updated_at: datetime
    comparison: EditionComparisonOut | None = None

    @classmethod
    def from_edition(
        cls, edition: SubscriptionEdition, comparison: EditionComparison | None = None
    ) -> "SubscriptionEditionOut":
        return cls(
            id=edition.id,
            subscription_id=edition.subscription_id,
            trigger=edition.trigger,
            due_at_utc=edition.due_at_utc,
            frozen_revision=edition.frozen_revision,
            requested=ObservationIntervalOut.from_interval(edition.requested),
            effective_intervals=[
                ObservationIntervalOut.from_interval(item) for item in edition.effective_intervals
            ],
            gaps=[ObservationIntervalOut.from_interval(item) for item in edition.gaps],
            workflow=edition.workflow,
            report_quality=edition.report_quality,
            coverage=edition.coverage,
            job_id=edition.job_id,
            report_id=edition.report_id,
            version_id=edition.version_id,
            covered_by_edition_id=edition.covered_by_edition_id,
            accepted_as_baseline=edition.accepted_as_baseline,
            safe_reason=edition.safe_reason,
            created_at=edition.created_at,
            updated_at=edition.updated_at,
            comparison=EditionComparisonOut.from_comparison(comparison)
            if comparison is not None
            else None,
        )


class SubscriptionEditionsOut(BaseModel):
    items: list[SubscriptionEditionOut]
    limit: int
    offset: int


class SubscriptionBaselineOut(BaseModel):
    subscription_id: UUID
    edition_id: UUID
    analytical_baseline_version_id: UUID
    covered_intervals: list[ObservationIntervalOut]
    complete_cutoff: datetime | None

    @classmethod
    def from_lineage(
        cls, lineage: SubscriptionLineage, edition_id: UUID
    ) -> "SubscriptionBaselineOut":
        if lineage.analytical_baseline_version_id is None:
            raise ValueError("An accepted baseline needs a saved version.")
        return cls(
            subscription_id=lineage.subscription_id,
            edition_id=edition_id,
            analytical_baseline_version_id=lineage.analytical_baseline_version_id,
            covered_intervals=[
                ObservationIntervalOut.from_interval(item) for item in lineage.covered_intervals
            ],
            complete_cutoff=lineage.complete_cutoff,
        )


class SubscriptionEventOut(BaseModel):
    id: UUID
    edition_id: UUID
    event_kind: str
    created_at: datetime

    @classmethod
    def from_delivery(cls, delivery: EditionDelivery) -> "SubscriptionEventOut":
        return cls(
            id=delivery.id,
            edition_id=delivery.edition_id,
            event_kind=delivery.event_kind,
            created_at=delivery.created_at,
        )


class SubscriptionEventsOut(BaseModel):
    items: list[SubscriptionEventOut]
    limit: int
    offset: int
