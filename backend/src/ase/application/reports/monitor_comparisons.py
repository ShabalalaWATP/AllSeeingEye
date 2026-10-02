"""Frozen checkpoint inputs and annotation-only meaningful-change classification."""

from collections import Counter
from dataclasses import replace
from datetime import datetime
from uuid import UUID

from ase.application.access import AccessContext
from ase.application.reports.claim_export_integrity import export_content_digest
from ase.application.reports.claim_export_selection import SelectClaimExport
from ase.application.reports.comparison_inputs import ComparisonSelection
from ase.application.reports.comparison_manifest import comparison_digest
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.annotation_comparison import (
    COMPARISON_METHOD,
    AnnotationComparison,
    AnnotationKind,
    ComparisonSide,
)
from ase.domain.annotation_deltas import annotation_deltas, annotation_rows, evidence_deltas
from ase.domain.annotation_monitoring import AnnotationMonitor, MonitorMode, WatchedRevision
from ase.domain.claim_revisions import ClaimRevision
from ase.domain.confidence_comparison import confidence_deltas
from ase.domain.errors import Conflict, InvalidRequest
from ase.domain.identity_review import IdentityDecisionRevision
from ase.domain.relationship_review import RelationshipReviewRevision


def watches_from_selection(value: ComparisonSelection) -> tuple[WatchedRevision, ...]:
    watches = tuple(
        [WatchedRevision("claim", v.claim_id, v.revision_id) for v in value.revisions]
        + [
            WatchedRevision("identity", v.decision_id, v.revision_id)
            for v in value.identity_revisions
        ]
        + [
            WatchedRevision("relationship", v.relationship_id, v.revision_id)
            for v in value.relationship_revisions
        ]
    )
    if not 1 <= len(watches) <= 20 or len({(w.kind, w.root_id) for w in watches}) != len(watches):
        raise InvalidRequest("Select one current revision for each of one to twenty watched roots.")
    return tuple(sorted(watches, key=lambda w: (w.kind, str(w.root_id))))


def validate_options(
    name: str,
    categories: tuple[AnnotationKind, ...],
    watches: tuple[WatchedRevision, ...],
    mode: MonitorMode = "selected_roots",
) -> None:
    if not name.strip() or len(name) > 120 or any(ord(c) < 32 for c in name):
        raise InvalidRequest("Choose a bounded monitor name without control characters.")
    if (
        not categories
        or len(categories) > 3
        or len(set(categories)) != len(categories)
        or not set(categories).issubset(
            {"claim", "identity", "relationship"}
            if mode == "report_inventory"
            else {w.kind for w in watches}
        )
    ):
        raise InvalidRequest("Choose applicable watched annotation categories once each.")


async def resolve_side(
    selector: SelectClaimExport,
    access: AccessContext,
    monitor: AnnotationMonitor,
    *,
    latest: bool = False,
) -> tuple[ComparisonSide, tuple[WatchedRevision, ...]]:
    record = await selector.claims.resolve_report(access, monitor.report_id)
    access.require_same_scope(
        monitor.created_by, monitor.team_id, record.created_by, record.team_id
    )
    version = await selector.claims.resolve_version(record.id, monitor.version_number)
    claims: list[ClaimRevision] = []
    identities: list[IdentityDecisionRevision] = []
    relationships: list[RelationshipReviewRevision] = []
    watches: list[WatchedRevision] = []
    for watch in monitor.watches:
        resolver = selector.annotation_resolvers.get(watch.kind)
        if resolver is None:
            raise InvalidRequest("A watched annotation kind is unavailable.")
        resolved = await resolver(access, watch.root_id, None if latest else watch.revision_id)
        claims.extend(resolved.claims)
        identities.extend(resolved.identities)
        relationships.extend(resolved.relationships)
        report_id, number = resolved.report_id, resolved.version_number
        if report_id != record.id or number != monitor.version_number:
            raise Conflict("A watched root no longer has its exact report anchor.")
        watches.append(replace(watch, revision_id=resolved.revision_id))
    result = ComparisonSide(
        record.id,
        version.id,
        version.number,
        record.title,
        version.period_from,
        version.period_to,
        version.created_at,
        version.data_cutoff,
        evidence_digest(version),
        export_content_digest(record, version),
        tuple(claims),
        tuple(identities),
        tuple(relationships),
        version.evidence,
        version.body.key_judgements,
        version.assessment,
    )
    annotation_rows(result)
    return result, tuple(watches)


def build_observation(
    before: ComparisonSide, after: ComparisonSide, actor: UUID, now: datetime
) -> AnnotationComparison:
    value = AnnotationComparison(
        COMPARISON_METHOD,
        now,
        "",
        actor,
        before,
        after,
        (),
        (),
        annotation_deltas(before, after, ()),
        evidence_deltas(before, after),
        confidence_deltas(before, after, ()),
    )
    return replace(value, comparison_sha256=comparison_digest(value))


def meaningful_categories(comparison: AnnotationComparison) -> tuple[AnnotationKind, ...]:
    # Timestamp/label recapture is provenance, while explanations remain analytical content.
    old, new = annotation_rows(comparison.before), annotation_rows(comparison.after)
    changed = set()
    for row in comparison.annotation_changes:
        fields = set(row.changed_fields) - {"capture_provenance"}
        if "unresolved_conflicts" in fields and row.before_revision_id and row.after_revision_id:
            before = old[(row.kind, row.before_revision_id)].unresolved_conflicts
            after = new[(row.kind, row.after_revision_id)].unresolved_conflicts
            if Counter(before) == Counter(after):
                fields.remove("unresolved_conflicts")
        if row.status in {"added", "removed"} or fields:
            changed.add(row.kind)
    return tuple(sorted(changed))
