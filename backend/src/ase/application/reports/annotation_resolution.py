"""Public typed annotation resolvers retain each kind's exact-anchor validation."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
from uuid import UUID

from ase.application.access import AccessContext
from ase.application.reports.claims import ReportClaims
from ase.application.reports.identities import ReportIdentities
from ase.application.reports.relationships import ReportRelationships
from ase.domain.annotation_comparison import AnnotationKind
from ase.domain.claim_revisions import ClaimRevision
from ase.domain.identity_review import IdentityDecisionRevision
from ase.domain.relationship_review import RelationshipReviewRevision


@dataclass(frozen=True, slots=True)
class ResolvedAnnotation:
    report_id: UUID
    version_number: int
    revision_id: UUID
    claims: tuple[ClaimRevision, ...] = ()
    identities: tuple[IdentityDecisionRevision, ...] = ()
    relationships: tuple[RelationshipReviewRevision, ...] = ()


AnnotationResolver = Callable[[AccessContext, UUID, UUID | None], Awaitable[ResolvedAnnotation]]


async def resolve_claim(
    service: ReportClaims, access: AccessContext, root_id: UUID, revision_id: UUID | None
) -> ResolvedAnnotation:
    root, version = await service.resolve_anchor(access, root_id)
    revision = await service.resolve_revision(root, version, revision_id or root.latest_revision_id)
    return ResolvedAnnotation(
        root.report_id, root.report_version_number, revision.id, claims=(revision,)
    )


async def resolve_identity(
    service: ReportIdentities, access: AccessContext, root_id: UUID, revision_id: UUID | None
) -> ResolvedAnnotation:
    root, version = await service.resolve_anchor(access, root_id)
    revision = await service.resolve_revision(root, version, revision_id or root.latest_revision_id)
    return ResolvedAnnotation(
        root.report_id, root.report_version_number, revision.id, identities=(revision,)
    )


async def resolve_relationship(
    service: ReportRelationships, access: AccessContext, root_id: UUID, revision_id: UUID | None
) -> ResolvedAnnotation:
    root, version = await service.resolve_anchor(access, root_id)
    revision = await service.resolve_revision(root, version, revision_id or root.latest_revision_id)
    return ResolvedAnnotation(
        root.report_id, root.report_version_number, revision.id, relationships=(revision,)
    )


def annotation_resolvers(
    claims: ReportClaims,
    identities: ReportIdentities | None,
    relationships: ReportRelationships | None,
) -> dict[AnnotationKind, AnnotationResolver]:
    resolvers: dict[AnnotationKind, AnnotationResolver] = {"claim": partial(resolve_claim, claims)}
    if identities is not None:
        resolvers["identity"] = partial(resolve_identity, identities)
    if relationships is not None:
        resolvers["relationship"] = partial(resolve_relationship, relationships)
    return resolvers
