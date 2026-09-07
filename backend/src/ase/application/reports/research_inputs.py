"""Authorise private input snapshots and bind follow-ups to an exact saved version."""

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.ports.reports import ReportRepository
from ase.application.ports.research_inputs import ResearchInputStore, StoredResearchInput
from ase.application.reports.request import ReportRequest
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.events import Event
from ase.domain.evidence import EvidenceItem
from ase.domain.report_records import ReportVersion
from ase.domain.reports import KeyJudgement
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchFocus
from ase.domain.users import User

if TYPE_CHECKING:
    from ase.application.reports.production_types import Job

PRIVATE_FOCUS = frozenset({ResearchFocus.DOCUMENT, ResearchFocus.MEDIA})


@dataclass(frozen=True, slots=True)
class ParentReference:
    report_id: UUID
    version: int
    owner_id: UUID


@dataclass(frozen=True, slots=True)
class PreparedResearchInputs:
    events: tuple[Event, ...] = ()
    evidence: tuple[EvidenceItem, ...] = ()
    judgements: tuple[KeyJudgement, ...] = ()
    attempts: tuple[CollectionAttempt, ...] = ()
    parent: ParentReference | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def apply(self, job: "Job") -> "Job":
        return replace(
            job,
            seed_events=self.events,
            reused_evidence=self.evidence,
            followup_judgements=self.judgements,
            seed_attempts=self.attempts,
            scope={**job.scope, **self.metadata},
        )


async def require_parent(
    access: AccessPolicy,
    reports: ReportRepository,
    actor: User,
    request: ReportRequest,
    reference: ParentReference,
) -> ReportVersion:
    """Require current read access and matching destination scope, never parent write access.

    The final caller holds the shared administration guard until the report is saved.
    A later parent version may exist; the bound immutable version is never replaced.
    """
    context = await access.context(actor)
    parent = await reports.get(reference.report_id)
    if parent is None:
        raise NotFound()
    context.require_same_scope(
        reference.owner_id, request.team_id, parent.created_by, parent.team_id
    )
    version = await reports.get_version(parent.id, reference.version)
    if version is None:
        raise NotFound()
    return version


def _input_metadata(stored: StoredResearchInput) -> dict[str, Any]:
    receipt = stored.receipt
    # The transient capability id, raw bytes and preview are deliberately not persisted.
    return {
        "filename": receipt.filename,
        "media_type": receipt.media_type,
        "sha256": receipt.sha256,
        "imported_at": receipt.imported_at.isoformat(),
        "extracted_items": receipt.event_count,
        "limitations": list(receipt.limitations),
    }


class ReportResearchInputs:
    def __init__(
        self, access: AccessPolicy, reports: ReportRepository, inputs: ResearchInputStore | None
    ) -> None:
        self._access, self._reports, self._inputs = access, reports, inputs

    async def prepare(
        self,
        actor: User,
        request: ReportRequest,
        previous: ReportVersion | None = None,
        *,
        owner_id: UUID | None = None,
    ) -> PreparedResearchInputs:
        events: tuple[Event, ...] = ()
        evidence: tuple[EvidenceItem, ...] = ()
        judgements: tuple[KeyJudgement, ...] = ()
        attempts: list[CollectionAttempt] = []
        metadata: dict[str, Any] = {}
        parent: ParentReference | None = None
        if request.research_input_id is not None:
            if (
                request.research_mode is None
                or request.research_focus not in PRIVATE_FOCUS
                or self._inputs is None
            ):
                raise InvalidRequest("Private input requires document or media research")
            current = await self._access.context(actor)
            stored = self._inputs.read(current.actor, request.research_input_id)
            events = stored.events
            metadata["research_input"] = _input_metadata(stored)
            attempts.append(
                CollectionAttempt(
                    "research-upload",
                    "Private uploaded input",
                    CollectionStatus.COMPLETED,
                    len(events),
                    "Newly supplied extracted content, not newly verified public reporting. "
                    + " ".join(stored.receipt.limitations)[:700],
                )
            )
        if request.parent_report_id is not None:
            # Resolve latest only once. Final revalidation uses this exact version number.
            record = await self._reports.get(request.parent_report_id)
            if record is None:
                raise NotFound()
            parent = ParentReference(
                record.id, request.parent_version or record.latest_version, owner_id or actor.id
            )
            version = await require_parent(self._access, self._reports, actor, request, parent)
            if record.scope.get("research_time_basis") == "recorded_time":
                raise InvalidRequest(
                    "Start a new historical request; ordinary follow-ups cannot "
                    "preserve this time policy"
                )
            if record.scope.get("map_origin"):
                raise InvalidRequest(
                    "Start area research from its saved map revision; "
                    "ordinary follow-ups cannot preserve that scope"
                )
            if record.scope.get("research_focus") in {"document", "media"} and (
                request.research_focus not in PRIVATE_FOCUS or request.research_mode is None
            ):
                raise InvalidRequest("Private-source follow-ups require document or media research")
            evidence, judgements = version.evidence, version.body.key_judgements
            metadata.update(parent_report_id=str(parent.report_id), parent_version=parent.version)
        if previous is not None and request.research_focus in PRIVATE_FOCUS:
            # Regeneration survives upload expiry by using the last saved, bounded evidence.
            evidence = previous.evidence
        if evidence:
            origin = (
                previous
                if previous is not None and request.research_focus in PRIVATE_FOCUS
                else None
            )
            source_id = origin.report_id if origin else parent.report_id if parent else None
            source_version = origin.number if origin else parent.version if parent else None
            metadata["research_reuse"] = {
                "report_id": str(source_id),
                "version": source_version,
                "evidence_items": len(evidence),
                "basis": "frozen_saved_evidence",
            }
            attempts.append(
                CollectionAttempt(
                    "research-reused-evidence",
                    "Previously saved evidence",
                    CollectionStatus.COMPLETED,
                    len(evidence),
                    f"Reused from report {source_id}, version {source_version}, "
                    "with original dates and grades. "
                    "No source was recollected or independently reverified for these items.",
                )
            )
        if request.research_focus in PRIVATE_FOCUS and (
            request.research_mode is None or not (events or evidence)
        ):
            raise InvalidRequest(
                "Document and media research requires a private input or an authorised saved report"
            )
        return PreparedResearchInputs(
            events, evidence, judgements, tuple(attempts), parent, metadata
        )
