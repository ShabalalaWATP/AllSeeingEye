"""Exact synthetic comparison sides and persisted same-root revision selections."""

from ase.application.reports.claim_export_selection import ClaimExportReference
from ase.application.reports.comparison_inputs import ComparisonInput, ComparisonSelection
from ase.domain.annotation_comparison import ComparisonSide
from test_claim_repository import seed
from test_saved_map_views import claims_for


def side(version, *, claims=(), identities=(), relationships=()):
    return ComparisonSide(
        version.report_id,
        version.id,
        version.number,
        "Fixture",
        version.period_from,
        version.period_to,
        version.created_at,
        version.data_cutoff,
        "a" * 64,
        "b" * 64,
        claims,
        identities,
        relationships,
        version.evidence,
        version.body.key_judgements,
        version.assessment,
    )


async def prepared(client, container, user):
    actor = await claims_for(client, container, user)
    report, version, revision = await seed(container, user)
    selection = ComparisonSelection(
        report.id, 1, (ClaimExportReference(revision.claim_id, revision.id),)
    )
    return actor, report, version, revision, ComparisonInput(selection, selection)
