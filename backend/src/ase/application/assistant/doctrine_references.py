"""The existing Ask Eye doctrine registry, pinned to verified public sources.

Manual verification: 14 September 2026. No runtime fetching or PDF ingestion.
Edition updates require source review and a deliberate metadata/hash change.
"""

from datetime import date

from ase.domain.doctrine_reference import (
    DoctrineExcerpt,
    DoctrineReference,
    validate_reference_pack,
)

RETRIEVED_ON = date(2026, 9, 14)
OGL = (
    "UK Crown copyright 2025; Open Government Licence v3.0, except where otherwise stated. "
    "Only the attributed short HTML excerpt is retained."
)

DOCTRINE_REFERENCES = (
    DoctrineReference(
        identifier="phia-uncertainty-2025",
        title="UK PHIA: Explaining Uncertainty in UK Intelligence Assessment",
        publisher="UK Government, Intelligence Analysis",
        url="https://www.gov.uk/government/publications/"
        "explaining-uncertainty-in-uk-intelligence-assessment/"
        "explaining-uncertainty-in-uk-intelligence-assessment",
        edition="Public guidance published 24 March 2025",
        version=None,
        publication_date="2025-03-24",
        date_basis="publication",
        retrieved_on=RETRIEVED_ON,
        verification_scope="public_guidance",
        catalogue_publisher="UK Government, Intelligence Analysis",
        catalogue_published_on=date(2025, 3, 24),
        catalogue_updated_on=None,
        publication_url="https://www.gov.uk/government/publications/"
        "explaining-uncertainty-in-uk-intelligence-assessment/"
        "explaining-uncertainty-in-uk-intelligence-assessment",
        summary=(
            "PHIA separates likelihood from confidence in a judgement's foundations. "
            "The seven-band Probability Yardstick expresses approximate likelihood; High, "
            "Moderate and Low confidence consider the information base, analytical rigour, "
            "and complexity and volatility. These terms do not establish model calibration."
        ),
        access_note="Public HTML guidance; no claim to possess PHIA's internal evaluation tool.",
        excerpt=DoctrineExcerpt(
            text="Clearly communicating uncertainty allows customers to take it into account "
            "when making decisions based on our assessment.",
            source_url="https://www.gov.uk/government/publications/"
            "explaining-uncertainty-in-uk-intelligence-assessment/"
            "explaining-uncertainty-in-uk-intelligence-assessment",
            locator="Introduction, paragraph immediately before PHIA Probability Yardstick",
            reuse_basis=OGL,
            sha256="e031c7c60b9de153cbaae982799fa8bedcb14031942cbce8b201b19fd85da268",
        ),
    ),
    DoctrineReference(
        identifier="phia-standards-2025",
        title="UK PHIA: Common Analytical Standards",
        publisher="UK Government, Intelligence Analysis",
        url="https://www.gov.uk/government/publications/phia-common-analytical-standards/"
        "phia-common-analytical-standards",
        edition="Public guidance published 24 March 2025",
        version=None,
        publication_date="2025-03-24",
        date_basis="publication",
        retrieved_on=RETRIEVED_ON,
        verification_scope="public_guidance",
        catalogue_publisher="UK Government, Intelligence Analysis",
        catalogue_published_on=date(2025, 3, 24),
        catalogue_updated_on=None,
        publication_url="https://www.gov.uk/government/publications/"
        "phia-common-analytical-standards/phia-common-analytical-standards",
        summary=(
            "The eight public standards address independence, clarity, comprehensive coverage, "
            "auditability, relevance, rigour, objectivity and timeliness. They require attention "
            "to material contrary evidence, alternative hypotheses, assumptions and change. "
            "Customer relevance does not authorise shaping an assessment to a preferred policy."
        ),
        access_note="Public HTML guidance; methodology reference, not proof of an event.",
        excerpt=DoctrineExcerpt(
            text="Analysts should produce and retain a fully referenced version of their "
            "products for audit purposes.",
            source_url="https://www.gov.uk/government/publications/"
            "phia-common-analytical-standards/phia-common-analytical-standards",
            locator="Auditable, first sentence",
            reuse_basis=OGL,
            sha256="6af3f5054901cdf5a64ec4eb0f4174e8389ac2ee34f2a831b9ad2f4500a5f88f",
        ),
    ),
    DoctrineReference(
        identifier="uk-mod-jdp-2-00",
        title="UK MOD JDP 2-00: Intelligence, Counter-intelligence and Security Support "
        "to Joint Operations",
        publisher="UK Ministry of Defence",
        url="https://www.gov.uk/government/publications/"
        "jdp-2-00-understanding-and-intelligence-support-to-joint-operations",
        edition="Fourth Edition",
        version=None,
        publication_date="2023-08",
        date_basis="edition_month",
        retrieved_on=RETRIEVED_ON,
        verification_scope="publication_metadata",
        catalogue_publisher="UK Ministry of Defence",
        catalogue_published_on=date(2011, 8, 1),
        catalogue_updated_on=date(2023, 8, 17),
        publication_url="https://assets.publishing.service.gov.uk/media/"
        "653a4b0780884d0013f71bb0/JDP_2_00_Ed_4_web.pdf",
        summary=(
            "UK joint-operations intelligence doctrine, fourth edition dated August 2023. "
            "The official catalogue describes intelligence functions, the intelligence cycle "
            "and support to joint operations. The 2011 catalogue creation date is not this "
            "edition's publication date. Consult the publication for its actual provisions."
        ),
        access_note=(
            "Official PDF title, edition and release conditions checked. PDF text is not stored "
            "or reproduced here; its MOD release conditions are separate from the HTML licence."
        ),
        excerpt=DoctrineExcerpt(
            text="Finally, it provides external readers with an explanation of MOD "
            "intelligence functions.",
            source_url="https://www.gov.uk/government/publications/"
            "jdp-2-00-understanding-and-intelligence-support-to-joint-operations",
            locator="Who should read this publication, final audience",
            reuse_basis="GOV.UK catalogue HTML under Open Government Licence v3.0, except "
            "where otherwise stated; no excerpt from the separately restricted PDF.",
            sha256="06c9792a2a9366911787c61fab8fcdaa59b5217329060a6bd01c59cc0133480a",
        ),
    ),
    DoctrineReference(
        identifier="nato-ajp-2-9-catalogue",
        title="NATO AJP-2.9: Allied Joint Doctrine for Open Source Intelligence (OSINT)",
        publisher="NATO",
        url="https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283399",
        edition="Edition B",
        version=None,
        publication_date="2025-08-20",
        date_basis="promulgation",
        retrieved_on=RETRIEVED_ON,
        verification_scope="catalogue_metadata",
        catalogue_publisher="US Defense Logistics Agency, ASSIST Quick Search",
        catalogue_published_on=None,
        # DLA's "Data updated" header is a dataset refresh, not this record's revision date.
        catalogue_updated_on=None,
        publication_url=None,
        summary=(
            "The official US DLA catalogue lists NATO AJP-2.9 Edition B as active, promulgated "
            "20 August 2025, for open source intelligence. This confirms catalogue metadata "
            "only. It does not expose a publication version number or verify the text's rules."
        ),
        access_note=(
            "Controlled distribution document. Publication text and version number were not "
            "retrieved or verified; no NATO accreditation or full compliance is claimed."
        ),
        excerpt=DoctrineExcerpt(
            text="ALLIED JOINT DOCTRINE FOR OPEN SOURCE INTELLIGENCE (OSINT)",
            source_url="https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283399",
            locator="AJP-2.9 public catalogue, Title field",
            reuse_basis="Short factual title from the public US government catalogue only; "
            "no licence to reproduce NATO publication text is asserted.",
            sha256="47e641072c8d629235168c8d7961aea067b4db227ebc7688d6aea97bde3a6414",
        ),
    ),
)

# A deliberate source review is required before updating this digest with the registry.
DOCTRINE_REFERENCE_PACK_SHA256 = "4e7be5ef5fb4d33b7d43f9e3e425048b8d60e9127d3fc0ae2e0111fd0f590a1a"
validate_reference_pack(DOCTRINE_REFERENCES, DOCTRINE_REFERENCE_PACK_SHA256)
