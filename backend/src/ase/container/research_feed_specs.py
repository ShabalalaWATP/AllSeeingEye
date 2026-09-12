"""Additional private feed capabilities, preserving their original publisher families."""

from dataclasses import replace

from ase.adapters.research.eonet_area import EonetAreaResearchProvider
from ase.adapters.research.openaq_area import OpenAqAreaResearchProvider
from ase.adapters.research.publisher import LIMITATIONS, PUBLISHER_SEEDS
from ase.adapters.research.usgs_area import UsgsAreaResearchProvider
from ase.container.research_spec import research_spec
from ase.domain.events import Category
from ase.domain.source_rating_catalog import ProvenanceRole
from ase.domain.sources import SourceKind, SourceSpec


def additional_feed_specs() -> tuple[SourceSpec, ...]:
    publishers = tuple(
        replace(
            research_spec(
                f"research_publisher_{seed.spec.id}",
                seed.spec.name,
                seed.spec.category,
                "Publisher-supplied headlines; official publication does not verify the claims.",
                "Local headline matching in the existing public feed and publication interval.",
                LIMITATIONS,
                seed.spec.licence_note,
                organisation=seed.spec.organisation,
                language=seed.spec.language,
                kind=SourceKind.RSS,
            ),
            flags=frozenset({"on_demand", "unassessed"}) | seed.spec.flags,
        )
        for seed in PUBLISHER_SEEDS
    )
    hazard_entries: tuple[
        tuple[
            type[UsgsAreaResearchProvider] | type[EonetAreaResearchProvider], str, ProvenanceRole
        ],
        ...,
    ] = (
        (UsgsAreaResearchProvider, "United States Geological Survey", "originator"),
        (EonetAreaResearchProvider, "NASA Earth Observatory", "aggregator"),
    )
    hazards = tuple(
        research_spec(
            provider.id,
            provider.name,
            Category.DISASTER,
            "Original public hazard observations, preserving existing event identities. "
            "Different collection endpoints do not add independent corroboration.",
            provider.spatial_scope,
            provider.temporal_scope,
            "One bounded external request after source selection; no background polling. "
            "Source-reported locations and dates have uncertainty. "
            "Empty results are not clearance.",
            organisation=organisation,
            role=role,
        )
        for provider, organisation, role in hazard_entries
    )
    openaq = research_spec(
        OpenAqAreaResearchProvider.id,
        OpenAqAreaResearchProvider.name,
        Category.HUMANITARIAN,
        "Stationary instrument readings relayed by OpenAQ with original provider attribution. "
        "Air quality is environmental context, not a disaster or health alert.",
        OpenAqAreaResearchProvider.spatial_scope,
        OpenAqAreaResearchProvider.temporal_scope,
        "Requires a server-side OpenAQ key. Per-dataset reuse permissions and dated licences "
        "are checked before admitting evidence; unsupported permissions are excluded.",
        organisation="OpenAQ",
        role="aggregator",
        requires_key=True,
    )
    return (*publishers, *hazards, openaq)
