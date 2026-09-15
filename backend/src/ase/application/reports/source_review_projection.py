"""Apply authorised scoped histories to a new snapshot of exact saved judgements."""

from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
from uuid import UUID, uuid4

from ase.application.ports.source_reviews import SourceReviewRepository
from ase.application.reports.source_assessment_projection import (
    build_source_assessment_projection,
    prepare_source_assessment_targets,
)
from ase.domain.report_records import ReportVersion
from ase.domain.source_assessment import (
    AssertionRatingRevision,
    IssuerAuthenticity,
    SourceRatingRevision,
)
from ase.domain.source_review_records import SourceReviewSnapshot
from ase.domain.source_reviews import (
    SourceReviewKind,
    SourceReviewScope,
    SourceReviewTarget,
    source_review_key,
)


def review_target(
    version: ReportVersion, label: str, judgement_id: str, subject: str
) -> SourceReviewTarget:
    matching = tuple(row for row in version.body.key_judgements if row.id == judgement_id)
    if len(matching) != 1:
        raise ValueError("Choose one unambiguous saved judgement.")
    targets = prepare_source_assessment_targets(
        version.id,
        replace(version.body, key_judgements=matching),
        version.evidence,
        subjects={judgement_id: subject},
    )
    evidence = next((row for row in targets.evidence if row.label == label), None)
    claim = next((row for row in targets.claims if row.judgement_id == judgement_id), None)
    if (
        evidence is None
        or claim is None
        or not any(use.capture_id == evidence.capture_id for use in claim.uses)
    ):
        raise ValueError("Choose evidence cited by the exact saved judgement.")
    return SourceReviewTarget(
        version.report_id,
        version.id,
        evidence.source_id,
        subject,
        evidence.capture_id,
        claim.claim_id,
    )


async def freeze_reviewed_sources(
    repository: SourceReviewRepository,
    version: ReportVersion,
    scope: SourceReviewScope,
    actor_id: UUID,
    subjects: Mapping[str, str],
    now: datetime,
) -> SourceReviewSnapshot:
    """No event grades are adopted; exact applied reviews supply qualitative axes only."""
    if any(item.captured_at > now for item in version.evidence):
        raise ValueError("The source review clock predates captured report evidence.")
    targets = prepare_source_assessment_targets(
        version.id, version.body, version.evidence, subjects=subjects
    )
    evidence = {row.capture_id: row for row in targets.evidence}
    sources: dict[tuple[str, str], tuple[SourceRatingRevision, ...]] = {}
    assertions: dict[tuple[str, str], tuple[AssertionRatingRevision, ...]] = {}
    authenticities: dict[str, IssuerAuthenticity] = {}
    seen: set[str] = set()
    decisions: set[str] = set()
    for claim in targets.claims:
        for use in claim.uses:
            target = SourceReviewTarget(
                version.report_id,
                version.id,
                evidence[use.capture_id].source_id,
                claim.subject,
                use.capture_id,
                claim.claim_id,
            )
            for kind in SourceReviewKind:
                key = source_review_key(scope, kind, target)
                if key in seen:
                    continue
                seen.add(key)
                history = await repository.history(scope, key)
                if not history:
                    continue
                decisions.add(history[-1].review.id)
                if kind is SourceReviewKind.RELIABILITY:
                    sources[(target.source_id, target.subject)] = tuple(
                        row.source_revision() for row in history
                    )
                elif kind is SourceReviewKind.CREDIBILITY:
                    assertions[(target.capture_id, target.claim_id)] = tuple(
                        row.assertion_revision() for row in history
                    )
                elif (authenticity := history[-1].authenticity) is not None:
                    if history[-1].review.recorded_at > now:
                        raise ValueError(
                            "A source snapshot cannot predate its authenticity review."
                        )
                    authenticities[target.capture_id] = authenticity
    original = version.source_assessment
    origins = (
        original.projection.origins
        if original is not None and original.projection is not None
        else None
    )
    projection = build_source_assessment_projection(
        targets,
        frozen_at=now,
        source_histories=sources,
        assertion_histories=assertions,
        authenticities=authenticities,
        origins=origins,
    )
    return SourceReviewSnapshot(
        uuid4(),
        version.report_id,
        version.id,
        scope,
        actor_id,
        now,
        projection,
        tuple(sorted(decisions)),
    )
