"""Release both immutable sides under one current-authority transaction."""

from ase.application.access import AccessContext
from ase.application.dto import AccessClaims
from ase.application.reports.claim_export_integrity import export_content_digest
from ase.application.reports.claim_export_selection import SelectClaimExport, SelectedClaimExport
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.errors import Conflict, InvalidRequest


async def recheck_comparison(
    selector: SelectClaimExport,
    actor: AccessClaims,
    snapshots: tuple[SelectedClaimExport, SelectedClaimExport],
) -> None:
    # Account, membership and supported report mutation paths share this guard.
    # No per-annotation get/commit may release it between the two sides.
    await selector.uow.rollback()
    try:
        access = await selector.claims._context(actor)
        for snapshot in snapshots:
            record = await selector.claims._report(access, snapshot.report_id)
            version = await selector.claims._version(snapshot.report_id, snapshot.version_number)
            if (
                actor.user_id != snapshot.actor_id
                or record.created_by != snapshot.owner_id
                or record.team_id != snapshot.team_id
                or version.id != snapshot.report_version_id
                or evidence_digest(version) != snapshot.evidence_sha256
                or export_content_digest(record, version) != snapshot.content_sha256
            ):
                raise Conflict("A selected comparison report changed while rendering.")
            await _revisions(selector, access, snapshot)
        await selector.uow.commit()
    except BaseException:
        await selector.uow.rollback()
        raise


async def _revisions(
    selector: SelectClaimExport, access: AccessContext, snapshot: SelectedClaimExport
) -> None:
    for reference, expected in zip(snapshot.references, snapshot.revisions, strict=True):
        root, anchor = await selector.claims._anchor(access, reference.claim_id)
        actual = await selector.claims._revision(root, anchor, reference.revision_id)
        if actual != expected:
            raise Conflict("A selected claim revision changed while rendering.")
    if snapshot.identity_references:
        if selector.identities is None:
            raise InvalidRequest("Identity comparison is unavailable.")
        for identity_reference, identity_expected in zip(
            snapshot.identity_references, snapshot.identity_revisions, strict=True
        ):
            identity_root, anchor = await selector.identities._anchor(
                access, identity_reference.decision_id
            )
            identity_actual = await selector.identities._revision(
                identity_root, anchor, identity_reference.revision_id
            )
            if identity_actual != identity_expected:
                raise Conflict("A selected identity revision changed while rendering.")
    if snapshot.relationship_references:
        if selector.relationships is None:
            raise InvalidRequest("Relationship comparison is unavailable.")
        for relationship_reference, relationship_expected in zip(
            snapshot.relationship_references, snapshot.relationship_revisions, strict=True
        ):
            relationship_root, anchor = await selector.relationships._anchor(
                access, relationship_reference.relationship_id
            )
            relationship_actual = await selector.relationships._revision(
                relationship_root, anchor, relationship_reference.revision_id
            )
            if relationship_actual != relationship_expected:
                raise Conflict("A selected relationship revision changed while rendering.")
