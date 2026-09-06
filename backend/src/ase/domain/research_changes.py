"""Deterministic differences between frozen report versions, not semantic verification."""

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Literal, TypedDict
from uuid import UUID

from ase.domain.report_records import ReportVersion
from ase.domain.reports import ReportStatus


class _Identity(TypedDict):
    report_id: UUID
    version_id: UUID
    previous_report_id: UUID | None
    previous_version_id: UUID | None


@dataclass(frozen=True, slots=True)
class ResearchChange:
    status: Literal["baseline", "unchanged", "changed", "unavailable"]
    report_id: UUID
    version_id: UUID
    previous_report_id: UUID | None = None
    previous_version_id: UUID | None = None
    baseline_version_id: UUID | None = None
    added: int = 0
    removed: int = 0
    updated: int = 0
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in ("baseline", "unchanged", "changed", "unavailable"):
            raise ValueError("Unknown research comparison status")
        if not isinstance(self.report_id, UUID) or not isinstance(self.version_id, UUID):
            raise ValueError("Comparison requires saved report and version identities")
        if any(
            type(value) is not int or not 0 <= value <= 1000
            for value in (self.added, self.removed, self.updated)
        ):
            raise ValueError("Comparison counts exceed evidence bounds")
        allowed = {
            "evidence_inventory_changed",
            "source_flags_changed",
            "evidence_relationships_changed",
            "engine_confidence_changed",
            "validation_findings_changed",
            "assessment_availability_changed",
        }
        if len(self.reasons) > len(allowed) or any(
            reason not in allowed for reason in self.reasons
        ):
            raise ValueError("Invalid comparison reasons")

    @property
    def summary(self) -> str:
        if self.status == "baseline":
            return "Baseline established. Future runs compare frozen evidence and assessments."
        if self.status == "unavailable":
            return (
                "Comparison unavailable for this failed report; the previous baseline is retained."
            )
        if self.status == "unchanged":
            return "No deterministic evidence or assessment changes detected."
        return (
            f"Evidence: {self.added} added, {self.removed} removed, {self.updated} changed. "
            + "; ".join(reason.replace("_", " ") for reason in self.reasons)
            + ". This does not establish semantic importance or factual accuracy."
        )


def change_to_dict(change: ResearchChange | None) -> dict[str, Any] | None:
    if change is None:
        return None
    return {
        key: str(value) if isinstance(value, UUID) else value
        for key, value in asdict(change).items()
    }


def change_from_dict(value: dict[str, Any] | None) -> ResearchChange | None:
    if value is None:
        return None
    data = dict(value)
    for key in (
        "report_id",
        "version_id",
        "previous_report_id",
        "previous_version_id",
        "baseline_version_id",
    ):
        data[key] = UUID(data[key]) if data.get(key) else None
    data["reasons"] = tuple(data.get("reasons", ()))
    return ResearchChange(**data)


def _evidence(version: ReportVersion) -> dict[tuple[str, str], tuple[str, tuple[str, ...]]]:
    return {
        (item.source_id, item.event_id): (item.content_hash, tuple(sorted(item.flags)))
        for item in version.evidence
    }


def _relationships(version: ReportVersion) -> tuple[Counter[Any], Counter[Any]]:
    identities = {item.label: (item.source_id, item.event_id) for item in version.evidence}
    relationships: Counter[Any] = Counter()
    confidences: Counter[Any] = Counter()
    if version.assessment is None:
        return relationships, confidences
    for judgement in version.assessment.judgements:
        support = tuple(
            sorted(
                {identities[label] for label in judgement.supporting_labels if label in identities}
            )
        )
        opposition = tuple(
            sorted(
                {
                    identities[label]
                    for label in judgement.contradicting_labels
                    if label in identities
                }
            )
        )
        relationships[(support, opposition)] += 1
        confidences[
            (
                support,
                opposition,
                judgement.confidence_ceiling.value,
                judgement.final_confidence.value,
            )
        ] += 1
    return relationships, confidences


def compare_reports(previous: ReportVersion | None, current: ReportVersion) -> ResearchChange:
    """Ignore prose, ordering and citation labels; inspect saved IDs, hashes and engine outputs.

    Removed evidence may simply have aged out of the requested time window. A hash
    difference is a content change, not proof of a correction or retraction. Existing
    source flags are compared verbatim; no correction status is inferred from wording.
    """
    identity: _Identity = {
        "report_id": current.report_id,
        "version_id": current.id,
        "previous_report_id": previous.report_id if previous else None,
        "previous_version_id": previous.id if previous else None,
    }
    if current.status is ReportStatus.FAILED:
        return ResearchChange(
            status="unavailable", baseline_version_id=previous.id if previous else None, **identity
        )
    if previous is None:
        return ResearchChange(status="baseline", baseline_version_id=current.id, **identity)
    old, new = _evidence(previous), _evidence(current)
    added, removed = len(new.keys() - old.keys()), len(old.keys() - new.keys())
    common = old.keys() & new.keys()
    updated = sum(old[key][0] != new[key][0] for key in common)
    reasons = []
    if added or removed or updated:
        reasons.append("evidence_inventory_changed")
    if any(old[key][1] != new[key][1] for key in common):
        reasons.append("source_flags_changed")
    old_links, old_confidence = _relationships(previous)
    new_links, new_confidence = _relationships(current)
    if old_links != new_links:
        reasons.append("evidence_relationships_changed")
    elif old_confidence != new_confidence:
        reasons.append("engine_confidence_changed")
    if Counter((item.rule, item.severity) for item in previous.findings) != Counter(
        (item.rule, item.severity) for item in current.findings
    ):
        reasons.append("validation_findings_changed")
    if (previous.assessment is None) != (current.assessment is None):
        reasons.append("assessment_availability_changed")
    return ResearchChange(
        status="changed" if reasons else "unchanged",
        baseline_version_id=current.id,
        added=added,
        removed=removed,
        updated=updated,
        reasons=tuple(reasons),
        **identity,
    )
