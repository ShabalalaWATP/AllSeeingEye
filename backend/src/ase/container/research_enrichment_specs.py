"""Catalogue metadata for imported sanctions and bounded humanitarian context."""

from ase.container.research_spec import research_spec as _spec
from ase.domain.events import Category
from ase.domain.sources import SourceSpec


def enrichment_specs() -> tuple[SourceSpec, ...]:
    specs: list[SourceSpec] = []
    specs.extend(
        _spec(
            f"research-designations-{authority}",
            name,
            Category.ECONOMIC,
            "Operator-imported designation snapshot; source authenticity not verified.",
            "Exact authority ID or full-name candidate matching, up to 20 results.",
            "Requires a validated local snapshot. Date, source hash and reuse terms retained. "
            "A name match is not verified identity or guilt; absence is not clearance.",
            organisation=organisation,
            role="originator",
        )
        for authority, name, organisation in (
            ("uksl", "UK Sanctions List imported snapshot", "UK FCDO"),
            ("ofac_sdn", "OFAC SDN imported snapshot", "US Treasury OFAC"),
            ("un_sc", "UN Security Council imported snapshot", "United Nations Security Council"),
            ("eu_fsf", "EU financial sanctions imported snapshot", "European Commission"),
        )
    )
    specs.extend(
        _spec(
            f"research-hapi-{topic}",
            f"HDX HAPI {topic}",
            Category.HUMANITARIAN,
            "HDX distributes source assertions; independent corroboration is not established.",
            "One bounded country page of dated administrative observations.",
            "At most 20 rows; not complete national totals. No conflict-event/ACLED endpoint. "
            "Requires an operator-generated application identifier. Dataset-specific terms apply.",
            organisation=organisation,
            role="aggregator",
            requires_key=True,
        )
        for topic, organisation in (
            ("idps", "IOM DTM"),
            ("food-security", "IPC"),
            ("operational-presence", "OCHA"),
        )
    )
    return tuple(specs)
