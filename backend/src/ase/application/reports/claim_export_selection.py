"""Resolve explicit claim revisions and recheck their parent scope before export delivery."""

from dataclasses import dataclass
from uuid import UUID

from ase.application.dto import AccessClaims
from ase.application.ports import UnitOfWork
from ase.application.ports.reports import ReportRepository
from ase.application.reports.claim_export_integrity import export_content_digest
from ase.application.reports.claims import ReportClaims
from ase.application.reports.identities import ReportIdentities
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.claim_revisions import ClaimRevision
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.identity_review import IdentityDecisionRevision
from ase.domain.report_records import ReportRecord, ReportVersion


@dataclass(frozen=True, slots=True)
class ClaimExportReference:
    claim_id: UUID
    revision_id: UUID


@dataclass(frozen=True, slots=True)
class IdentityExportReference:
    decision_id: UUID
    revision_id: UUID


@dataclass(frozen=True, slots=True)
class SelectedClaimExport:
    actor_id: UUID
    report_id: UUID
    report_version_id: UUID
    version_number: int
    owner_id: UUID
    team_id: UUID | None
    evidence_sha256: str
    content_sha256: str
    references: tuple[ClaimExportReference, ...]
    revisions: tuple[ClaimRevision, ...]
    record: ReportRecord
    version: ReportVersion
    identity_references: tuple[IdentityExportReference, ...] = ()
    identity_revisions: tuple[IdentityDecisionRevision, ...] = ()


class SelectClaimExport:
    def __init__(
        self,
        claims: ReportClaims,
        reports: ReportRepository,
        uow: UnitOfWork,
        identities: ReportIdentities | None = None,
    ) -> None:
        self.claims, self.reports, self.uow = claims, reports, uow
        self.identities = identities

    async def resolve(
        self,
        actor: AccessClaims,
        report_id: UUID,
        number: int,
        references: tuple[ClaimExportReference, ...],
        *,
        identity_references: tuple[IdentityExportReference, ...] = (),
        allow_empty: bool = False,
    ) -> SelectedClaimExport:
        if type(number) is not int or not 1 <= number <= 2_147_483_647:
            raise InvalidRequest("Choose a positive report version.")
        if (
            not isinstance(references, tuple)
            or not isinstance(identity_references, tuple)
            or not (0 if allow_empty else 1) <= len(references) + len(identity_references) <= 20
        ):
            raise InvalidRequest("Select between one and twenty exact annotation revisions.")
        if len({item.revision_id for item in references}) != len(references):
            raise InvalidRequest("Each selected revision must be unique.")
        revisions = []
        identity_revisions = []
        anchors = set()
        for reference in references:
            root, revision = await self.claims.get(actor, reference.claim_id, reference.revision_id)
            if root.report_id != report_id or root.report_version_number != number:
                raise InvalidRequest("Selected revisions must belong to the chosen report version.")
            anchors.add((root.report_version_id, root.evidence_sha256))
            revisions.append(revision)
        if len({item.revision_id for item in identity_references}) != len(identity_references):
            raise InvalidRequest("Each selected identity revision must be unique.")
        for identity_reference in identity_references:
            if self.identities is None:
                raise InvalidRequest("Identity revision export is unavailable.")
            identity_root, identity_revision = await self.identities.get(
                actor, identity_reference.decision_id, identity_reference.revision_id
            )
            if (
                identity_root.report_id != report_id
                or identity_root.report_version_number != number
            ):
                raise InvalidRequest("Selected revisions must belong to the chosen report version.")
            anchors.add((identity_root.report_version_id, identity_root.evidence_sha256))
            identity_revisions.append(identity_revision)
        if not references and not identity_references:
            access = await self.claims._context(actor)
            await self.claims._report(access, report_id)
            await self.claims._version(report_id, number)
        record = await self.reports.get(report_id)
        version = await self.reports.get_version(report_id, number)
        if record is None or version is None:
            raise NotFound()
        digest = evidence_digest(version)
        if anchors and anchors != {(version.id, digest)}:
            raise Conflict("Selected claims have inconsistent frozen evidence anchors.")
        snapshot = SelectedClaimExport(
            actor.user_id,
            report_id,
            version.id,
            number,
            record.created_by,
            record.team_id,
            digest,
            export_content_digest(record, version),
            references,
            tuple(revisions),
            record,
            version,
            identity_references,
            tuple(identity_revisions),
        )
        await self.uow.commit()
        return snapshot

    async def recheck(self, actor: AccessClaims, snapshot: SelectedClaimExport) -> None:
        """Each get refreshes session/parent authority, never a cached export decision."""
        if actor.user_id != snapshot.actor_id:
            raise Conflict("The exporting account has changed.")
        await self.uow.rollback()
        fresh = await self.resolve(
            actor,
            snapshot.report_id,
            snapshot.version_number,
            snapshot.references,
            identity_references=snapshot.identity_references,
            allow_empty=not snapshot.references and not snapshot.identity_references,
        )
        if (
            fresh.report_version_id != snapshot.report_version_id
            or fresh.owner_id != snapshot.owner_id
            or fresh.team_id != snapshot.team_id
            or fresh.evidence_sha256 != snapshot.evidence_sha256
            or fresh.revisions != snapshot.revisions
            or fresh.identity_revisions != snapshot.identity_revisions
            or fresh.content_sha256 != snapshot.content_sha256
            or export_content_digest(snapshot.record, snapshot.version) != snapshot.content_sha256
        ):
            raise Conflict("The selected claim export changed while rendering.")
