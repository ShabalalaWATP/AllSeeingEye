"""Project frozen report versions into the deterministic edition comparison contract."""

from hashlib import sha256
from unicodedata import normalize

from ase.domain.evidence import EvidenceItem
from ase.domain.report_records import ReportVersion
from ase.domain.research_changes import (
    ChangeClassification,
    ComparisonClaim,
    ComparisonEvidence,
    ComparisonInput,
    classify_research_change,
)
from ase.domain.subscription_editions import EditionCoverage


def _fingerprint(text: str) -> str:
    canonical = " ".join(normalize("NFKC", text).split())
    return sha256(canonical.encode("utf-8")).hexdigest()


def _attributes(item: EvidenceItem) -> dict[str, object]:
    return {attribute.key: attribute.value for attribute in item.attributes}


def _evidence(item: EvidenceItem) -> ComparisonEvidence:
    attributes = _attributes(item)
    original_hash = attributes.get("original_sha256")
    previous_hash = attributes.get("previous_sha256")
    canonical_url = attributes.get("canonical_url")
    return ComparisonEvidence(
        evidence_id=f"{item.source_id}:{item.event_id}",
        content_hash=original_hash if isinstance(original_hash, str) else item.content_hash,
        origin_id=item.story_id or item.independence_key,
        canonical_url=canonical_url if isinstance(canonical_url, str) else item.url,
        correction_of_hash=previous_hash if isinstance(previous_hash, str) else None,
    )


def _claims(version: ReportVersion) -> tuple[ComparisonClaim, ...]:
    evidence = {
        item.label: f"{item.source_id}:{item.event_id}:{item.content_hash}"
        for item in version.evidence
    }
    return tuple(
        ComparisonClaim(
            claim_id=item.id,
            meaning_fingerprint=_fingerprint(item.statement),
            likelihood_band=item.probability.value,
            support=tuple(
                sorted(evidence[label] for label in item.supporting_evidence if label in evidence)
            ),
            opposition=tuple(
                sorted(
                    evidence[label] for label in item.contradicting_evidence if label in evidence
                )
            ),
            assumptions=tuple(sorted(item.assumptions)),
            indicators=tuple(sorted(item.indicators)),
        )
        for item in version.body.key_judgements
    )


def compare_subscription_versions(
    previous: ReportVersion | None,
    current: ReportVersion,
    coverage: EditionCoverage,
    *,
    baseline_expected: bool,
    baseline_compatible: bool = True,
) -> ChangeClassification:
    """Compare exact snapshots without treating model materiality labels as factual alerts."""
    return classify_research_change(
        ComparisonInput(
            previous_claims=_claims(previous) if previous is not None else (),
            current_claims=_claims(current),
            previous_evidence=tuple(_evidence(item) for item in previous.evidence)
            if previous is not None
            else (),
            current_evidence=tuple(_evidence(item) for item in current.evidence),
            coverage=coverage,
            baseline_available=previous is not None,
            baseline_compatible=baseline_compatible
            and (not baseline_expected or previous is not None),
            current_failed=current.status.value == "failed",
        )
    )
