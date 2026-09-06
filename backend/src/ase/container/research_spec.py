"""Common unassessed research capability metadata, never runtime availability."""

from datetime import timedelta

from ase.domain.events import Category, Reliability
from ase.domain.source_rating_catalog import ProvenanceRole
from ase.domain.source_ratings import SOURCE_RATING_POLICY_VERSION, SourceRating
from ase.domain.sources import SourceKind, SourceSpec

COMMON_LIMITATIONS = (
    "Reliability remains unassessed (F); collection does not verify individual claims, "
    "publishers, accounts or uploaders. No measured accuracy or review date is recorded.",
    "This catalogue describes supported capabilities, not current availability, credentials "
    "or successful collection. Report collection receipts record actual coverage.",
)


def research_spec(
    id_: str,
    name: str,
    category: Category,
    basis: str,
    scope: str,
    *limitations: str,
    organisation: str = "",
    role: ProvenanceRole = "unassessed",
    language: str = "en",
    kind: SourceKind = SourceKind.API,
    requires_key: bool = False,
) -> SourceSpec:
    # Empty organisations share unknown provenance and establish no independent origin.
    # Named collector organisations group endpoints, not the underlying claims.
    return SourceSpec(
        id=id_,
        name=name,
        organisation=organisation,
        category=category,
        kind=kind,
        url="",
        reliability=Reliability.F,
        poll_interval=timedelta(days=1),
        language=language,
        requires_key=requires_key,
        flags=frozenset({"on_demand", "unassessed"}),
        rating=SourceRating(
            policy_version=SOURCE_RATING_POLICY_VERSION,
            status="unassessed",
            assessed_grade=None,
            basis=basis,
            scope=scope,
            limitations=(*COMMON_LIMITATIONS, *limitations),
            provenance_role=role,
            publisher_reliability_assessed=False,
        ),
    )
