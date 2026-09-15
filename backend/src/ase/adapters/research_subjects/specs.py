"""Registry descriptions for on-demand providers, not polling connectors."""

from datetime import timedelta

from ase.domain.events import Category, Reliability
from ase.domain.source_ratings import SOURCE_RATING_POLICY_VERSION, SourceRating
from ase.domain.sources import SourceKind, SourceSpec


def subject_specs() -> tuple[SourceSpec, ...]:
    entries = (
        (
            "research-openalex",
            "OpenAlex scholarly metadata",
            "",
            Category.NEWS,
            "https://api.openalex.org/works",
            "https://help.openalex.org/data/works/",
            "Opt-in metadata search. OpenAlex aggregates Crossref and other sources; "
            "independent corroboration is not established. "
            "No full text; retraction flags require review. An optional operator API key "
            "uses its account allowance; otherwise anonymous limits apply.",
        ),
        (
            "research-crossref",
            "Crossref scholarly metadata",
            "",
            Category.NEWS,
            "https://api.crossref.org/works",
            "https://www.crossref.org/documentation/retrieve-metadata/",
            "Opt-in scholarly metadata. Publisher-deposited metadata and update notices, "
            "not independent review of research. "
            "Overlap with OpenAlex is expected; notice targets are not the notice DOI.",
        ),
        (
            "research-world-bank",
            "World Bank annual indicators",
            "World Bank",
            Category.ECONOMIC,
            "https://api.worldbank.org/v2",
            "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392",
            "Explicit country, indicator and at most 20 annual periods. "
            "Current series snapshot, not historical vintages. "
            "Preserve supplied units and missing values. Underlying dataset terms may vary.",
        ),
        (
            "research-ons-cpih",
            "ONS UK CPIH monthly observations",
            "Office for National Statistics",
            Category.ECONOMIC,
            "https://api.beta.ons.gov.uk/v1/datasets/cpih01",
            "https://developer.ons.gov.uk/observations/cmd/",
            "Explicit ONS:CPIH:<version> subject, United Kingdom only and at most 24 monthly "
            "periods under recorded-time semantics. The selected version is not a latest-version "
            "claim. Preserve units, null values and the exact ONS version. OGL v3.0 attribution "
            "is required.",
        ),
        (
            "research-uk-parliament",
            "UK Parliament written questions",
            "UK Parliament",
            Category.POLITICAL,
            "https://questions-statements-api.parliament.uk/api/writtenquestions/questions",
            "https://questions-statements-api.parliament.uk/index.html",
            "Opt-in current written-question and answer metadata; no linked documents. "
            "Official record of attributed assertions, not independent verification. "
            "Review Parliament reuse terms.",
        ),
    )
    return tuple(
        SourceSpec(
            id=id_,
            name=name,
            organisation=organisation,
            category=category,
            kind=SourceKind.API,
            url="",
            reliability=Reliability.F,
            poll_interval=timedelta(hours=24),
            homepage="",
            licence_note=note,
            rating=SourceRating(
                policy_version=SOURCE_RATING_POLICY_VERSION,
                status="unassessed",
                assessed_grade=None,
                basis="No measured source or item reliability assessment is recorded.",
                scope=f"On-demand {name.lower()}; records and assertions remain unverified.",
                limitations=(
                    "Catalogue registration does not establish current service availability; "
                    "inspect the saved collection receipt for actual coverage.",
                    note,
                    "Unknown does not mean false; no reliability is inherited from the host.",
                ),
                provenance_role="aggregator" if not organisation else "originator",
                publisher_reliability_assessed=False,
            ),
        )
        for id_, name, organisation, category, url, homepage, note in entries
    )
