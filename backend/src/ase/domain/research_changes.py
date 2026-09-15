"""Deterministic differences between frozen report versions, not semantic verification."""

from dataclasses import dataclass
from enum import StrEnum

from ase.domain.research_change_legacy import (
    ResearchChange,
    change_from_dict,
    change_to_dict,
    compare_reports,
)
from ase.domain.subscription_editions import EditionCoverage

__all__ = (
    "ChangeClassification",
    "ComparisonClaim",
    "ComparisonEvidence",
    "ComparisonInput",
    "ComparisonReason",
    "ComparisonState",
    "ResearchChange",
    "change_from_dict",
    "change_to_dict",
    "classify_research_change",
    "compare_reports",
)


class ComparisonState(StrEnum):
    FAILURE = "failure"
    INSUFFICIENT_COVERAGE = "insufficient_coverage"
    SIGNIFICANT_CONTRADICTION_OR_CORRECTION = "significant_contradiction_or_correction"
    ASSESSMENT_CHANGED = "assessment_changed"
    NEW_EVIDENCE_UNCHANGED_ASSESSMENT = "new_evidence_broadly_unchanged_assessment"
    NO_NEW_RELEVANT_EVIDENCE = "no_new_relevant_captured_evidence"


class ComparisonReason(StrEnum):
    CURRENT_RUN_FAILED = "current_run_failed"
    BASELINE_UNAVAILABLE = "baseline_unavailable"
    BASELINE_INCOMPATIBLE = "baseline_incompatible"
    PROVIDER_OUTAGE = "provider_outage"
    COVERAGE_INADEQUATE = "coverage_inadequate"
    SIGNIFICANT_CONTRADICTION = "significant_contradiction"
    SOURCE_CORRECTION = "source_correction"
    CLAIM_INVENTORY_CHANGED = "claim_inventory_changed"
    CLAIM_MAPPING_UNRESOLVED = "claim_mapping_unresolved"
    CLAIM_MEANING_CHANGED = "claim_meaning_changed"
    LIKELIHOOD_CHANGED = "likelihood_changed"
    HORIZON_CHANGED = "horizon_changed"
    SUPPORT_CHANGED = "support_changed"
    OPPOSITION_CHANGED = "opposition_changed"
    ASSUMPTIONS_CHANGED = "assumptions_changed"
    INDICATORS_CHANGED = "indicators_changed"
    NEW_RELEVANT_EVIDENCE = "new_relevant_evidence"
    SYNDICATED_DUPLICATES_ONLY = "syndicated_duplicates_only"
    ADEQUATE_COVERAGE_NO_NEW_EVIDENCE = "adequate_coverage_no_new_evidence"


@dataclass(frozen=True, slots=True)
class ComparisonClaim:
    claim_id: str
    meaning_fingerprint: str
    likelihood_band: str | None = None
    horizon_fingerprint: str | None = None
    support: tuple[str, ...] = ()
    opposition: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    indicators: tuple[str, ...] = ()
    significant_contradiction: bool = False

    def __post_init__(self) -> None:
        if not self.claim_id or not self.meaning_fingerprint:
            raise ValueError("Comparison claims require stable identity and meaning.")


@dataclass(frozen=True, slots=True)
class ComparisonEvidence:
    evidence_id: str
    content_hash: str
    origin_id: str
    canonical_url: str | None = None
    correction_of_hash: str | None = None
    relevant: bool = True

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.content_hash or not self.origin_id:
            raise ValueError("Comparison evidence requires identity, content and origin.")


@dataclass(frozen=True, slots=True)
class ComparisonInput:
    previous_claims: tuple[ComparisonClaim, ...] = ()
    current_claims: tuple[ComparisonClaim, ...] = ()
    previous_evidence: tuple[ComparisonEvidence, ...] = ()
    current_evidence: tuple[ComparisonEvidence, ...] = ()
    coverage: EditionCoverage = EditionCoverage.UNKNOWN
    baseline_available: bool = True
    baseline_compatible: bool = True
    current_failed: bool = False
    attempted_providers: tuple[str, ...] = ()
    successful_providers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not set(self.successful_providers) <= set(self.attempted_providers):
            raise ValueError("Successful providers must have been attempted.")
        if any(
            len({item.claim_id for item in claims}) != len(claims)
            for claims in (self.previous_claims, self.current_claims)
        ):
            raise ValueError("Claim mappings must be unambiguous.")
        if any(
            len({item.evidence_id for item in evidence}) != len(evidence)
            for evidence in (self.previous_evidence, self.current_evidence)
        ):
            raise ValueError("Evidence identities must be unique per version.")


@dataclass(frozen=True, slots=True)
class ChangeClassification:
    state: ComparisonState
    reasons: tuple[ComparisonReason, ...]
    changed_claim_ids: tuple[str, ...] = ()
    corrected_evidence_ids: tuple[str, ...] = ()
    novel_evidence_ids: tuple[str, ...] = ()
    syndicated_duplicate_ids: tuple[str, ...] = ()


_CLAIM_FIELDS = (
    ("meaning_fingerprint", ComparisonReason.CLAIM_MEANING_CHANGED),
    ("likelihood_band", ComparisonReason.LIKELIHOOD_CHANGED),
    ("horizon_fingerprint", ComparisonReason.HORIZON_CHANGED),
    ("support", ComparisonReason.SUPPORT_CHANGED),
    ("opposition", ComparisonReason.OPPOSITION_CHANGED),
    ("assumptions", ComparisonReason.ASSUMPTIONS_CHANGED),
    ("indicators", ComparisonReason.INDICATORS_CHANGED),
)


def _unresolved_claim_ids(
    old_claims: dict[str, ComparisonClaim], new_claims: dict[str, ComparisonClaim]
) -> set[str]:
    """Flag identity reuse/reassignment where exact meaning appears under other IDs."""
    old_by_meaning: dict[str, set[str]] = {}
    new_by_meaning: dict[str, set[str]] = {}
    for by_meaning, claims in ((old_by_meaning, old_claims), (new_by_meaning, new_claims)):
        for claim_id, claim in claims.items():
            by_meaning.setdefault(claim.meaning_fingerprint, set()).add(claim_id)
    return set().union(
        *(
            old_by_meaning[meaning] | new_by_meaning[meaning]
            for meaning in old_by_meaning.keys() & new_by_meaning.keys()
            if old_by_meaning[meaning] != new_by_meaning[meaning]
        )
    )


def classify_research_change(value: ComparisonInput) -> ChangeClassification:  # noqa: PLR0912, PLR0915
    """Classify frozen projections with fixed precedence and ordered reasons."""
    reasons: list[ComparisonReason] = []
    if value.current_failed:
        reasons.append(ComparisonReason.CURRENT_RUN_FAILED)
    if not value.baseline_available:
        reasons.append(ComparisonReason.BASELINE_UNAVAILABLE)
    if not value.baseline_compatible:
        reasons.append(ComparisonReason.BASELINE_INCOMPATIBLE)
    outage = bool(value.attempted_providers) and not value.successful_providers
    if outage:
        reasons.append(ComparisonReason.PROVIDER_OUTAGE)
    if value.coverage is not EditionCoverage.COMPLETE_FOR_PLAN:
        reasons.append(ComparisonReason.COVERAGE_INADEQUATE)

    old_claims = {item.claim_id: item for item in value.previous_claims}
    new_claims = {item.claim_id: item for item in value.current_claims}
    changed = set(old_claims) ^ set(new_claims)
    if changed:
        reasons.append(ComparisonReason.CLAIM_INVENTORY_CHANGED)
    unresolved = _unresolved_claim_ids(old_claims, new_claims)
    if unresolved:
        changed.update(unresolved)
        reasons.append(ComparisonReason.CLAIM_MAPPING_UNRESOLVED)
    for claim_id in sorted(old_claims.keys() & new_claims.keys()):
        if claim_id in unresolved:
            continue
        old, new = old_claims[claim_id], new_claims[claim_id]
        for field, reason in _CLAIM_FIELDS:
            if getattr(old, field) != getattr(new, field):
                changed.add(claim_id)
                if reason not in reasons:
                    reasons.append(reason)
    if any(item.significant_contradiction for item in value.current_claims):
        reasons.append(ComparisonReason.SIGNIFICANT_CONTRADICTION)

    old_evidence = {item.evidence_id: item for item in value.previous_evidence}
    old_origins = {
        (item.origin_id, item.content_hash) for item in value.previous_evidence if item.relevant
    }
    old_url_hashes = {
        (item.canonical_url, item.content_hash)
        for item in value.previous_evidence
        if item.canonical_url
    }
    seen_origins = set(old_origins)
    novel: set[str] = set()
    syndicated: set[str] = set()
    corrected: set[str] = set()
    for item in sorted(value.current_evidence, key=lambda evidence: evidence.evidence_id):
        if (item.canonical_url, item.correction_of_hash) in old_url_hashes:
            corrected.add(item.evidence_id)
        if item.relevant and item.evidence_id not in old_evidence:
            origin = (item.origin_id, item.content_hash)
            target = syndicated if origin in seen_origins else novel
            target.add(item.evidence_id)
            seen_origins.add(origin)
    if corrected:
        reasons.append(ComparisonReason.SOURCE_CORRECTION)
    if novel:
        reasons.append(ComparisonReason.NEW_RELEVANT_EVIDENCE)
    if syndicated and not novel:
        reasons.append(ComparisonReason.SYNDICATED_DUPLICATES_ONLY)

    semantic = {reason for _, reason in _CLAIM_FIELDS} | {ComparisonReason.CLAIM_INVENTORY_CHANGED}
    inadequate = any(
        (
            not value.baseline_available,
            not value.baseline_compatible,
            outage,
            bool(unresolved),
            value.coverage is not EditionCoverage.COMPLETE_FOR_PLAN,
        )
    )
    if value.current_failed:
        state = ComparisonState.FAILURE
    elif inadequate:
        state = ComparisonState.INSUFFICIENT_COVERAGE
    elif corrected or ComparisonReason.SIGNIFICANT_CONTRADICTION in reasons:
        state = ComparisonState.SIGNIFICANT_CONTRADICTION_OR_CORRECTION
    elif semantic.intersection(reasons):
        state = ComparisonState.ASSESSMENT_CHANGED
    elif novel:
        state = ComparisonState.NEW_EVIDENCE_UNCHANGED_ASSESSMENT
    else:
        state = ComparisonState.NO_NEW_RELEVANT_EVIDENCE
        reasons.append(ComparisonReason.ADEQUATE_COVERAGE_NO_NEW_EVIDENCE)
    return ChangeClassification(
        state=state,
        reasons=tuple(reasons),
        changed_claim_ids=tuple(sorted(changed)),
        corrected_evidence_ids=tuple(sorted(corrected)),
        novel_evidence_ids=tuple(sorted(novel)),
        syndicated_duplicate_ids=tuple(sorted(syndicated)),
    )
