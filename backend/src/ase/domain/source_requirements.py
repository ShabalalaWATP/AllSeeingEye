"""The source mix each product template expects, as rows an operator can read.

Depth caps decide how many sources a report uses. These rows decide what kind: a cyber
summary that never sees a vendor advisory or a national CERT is thin in a way its
length does not show. A template with no row expects no particular mix, only that the
report does not quietly rest on one organisation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ase.domain.source_character import CHARACTER_LABELS, SourceCharacter, characters_of

if TYPE_CHECKING:
    from ase.domain.evidence import EvidenceItem


@dataclass(frozen=True, slots=True)
class SourceRequirement:
    """One expectation about the mix, with the words used when it is not met."""

    id: str
    description: str
    characters: frozenset[SourceCharacter]
    minimum: int = 1
    # Wording that shows the report already discloses the gap in its own sourcing.
    gap_cues: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TemplateSourcePolicy:
    requirements: tuple[SourceRequirement, ...] = ()
    minimum_organisations: int = 2


@dataclass(frozen=True, slots=True)
class SourceSufficiency:
    template_id: str
    organisations: int
    minimum_organisations: int
    met: tuple[str, ...]
    unmet: tuple[SourceRequirement, ...]

    @property
    def single_organisation(self) -> bool:
        return self.organisations <= 1


def _requirement(
    id_: str,
    description: str,
    *characters: SourceCharacter,
    minimum: int = 1,
    cues: tuple[str, ...] = (),
) -> SourceRequirement:
    return SourceRequirement(id_, description, frozenset(characters), minimum, cues)


_VENDOR_ADVISORY = _requirement(
    "vendor_advisory",
    "a security vendor or research team advisory",
    SourceCharacter.SECURITY_VENDOR,
    cues=("vendor advisory", "vendor advisories", "no vendor"),
)
_NATIONAL_CERT = _requirement(
    "national_cert",
    "a national CERT or government cyber authority",
    SourceCharacter.NATIONAL_CERT,
    cues=("national cert", "cert advisory", "no cert"),
)
_OFFICIAL_ISSUER = _requirement(
    "official_issuer",
    "an official issuer such as a government department or an international body",
    SourceCharacter.OFFICIAL_ISSUER,
    cues=("official issuer", "no official"),
)
_INDEPENDENT_OUTLET = _requirement(
    "independent_outlet",
    "an independent news outlet not aligned with a party to the subject",
    SourceCharacter.INDEPENDENT_OUTLET,
    cues=("independent outlet", "no independent"),
)
_INDEPENDENT_VIEW = _requirement(
    "independent_view",
    "an independent outlet or a research body",
    SourceCharacter.INDEPENDENT_OUTLET,
    SourceCharacter.RESEARCH_BODY,
    cues=("independent outlet", "research body", "no independent"),
)
_HUMANITARIAN = _requirement(
    "humanitarian_agency",
    "a humanitarian agency reporting on impact and response",
    SourceCharacter.HUMANITARIAN_AGENCY,
    cues=("humanitarian agency", "no humanitarian"),
)
_OBSERVED_FACTS = _requirement(
    "observed_facts",
    "instrument data or an official issuer for the event facts",
    SourceCharacter.INSTRUMENT,
    SourceCharacter.OFFICIAL_ISSUER,
    cues=("instrument data", "no instrument"),
)
_INSTRUMENT = _requirement(
    "instrument",
    "instrument or sensor data",
    SourceCharacter.INSTRUMENT,
    cues=("instrument data", "no instrument"),
)

TEMPLATE_SOURCE_POLICIES: dict[str, TemplateSourcePolicy] = {
    "intsum": TemplateSourcePolicy(minimum_organisations=3),
    "intrep": TemplateSourcePolicy(minimum_organisations=2),
    "country_brief": TemplateSourcePolicy(
        requirements=(_OFFICIAL_ISSUER, _INDEPENDENT_OUTLET), minimum_organisations=2
    ),
    "ask": TemplateSourcePolicy(minimum_organisations=2),
    "disaster_sitrep": TemplateSourcePolicy(
        requirements=(_OBSERVED_FACTS, _HUMANITARIAN), minimum_organisations=2
    ),
    "conflict_assessment": TemplateSourcePolicy(
        requirements=(_INDEPENDENT_VIEW,), minimum_organisations=3
    ),
    "aviation_activity": TemplateSourcePolicy(requirements=(_INSTRUMENT,), minimum_organisations=1),
    "maritime_activity": TemplateSourcePolicy(
        requirements=(_OFFICIAL_ISSUER,), minimum_organisations=1
    ),
    "cyber_summary": TemplateSourcePolicy(
        requirements=(_VENDOR_ADVISORY, _NATIONAL_CERT), minimum_organisations=2
    ),
}

DEFAULT_POLICY = TemplateSourcePolicy()


def policy_for(template_id: str) -> TemplateSourcePolicy:
    return TEMPLATE_SOURCE_POLICIES.get(template_id, DEFAULT_POLICY)


def _organisation(item: EvidenceItem) -> str:
    return item.independence_key.strip() or item.source_id


def assess_source_mix(template_id: str, cited: Sequence[EvidenceItem]) -> SourceSufficiency:
    """Count the distinct organisations behind each expected kind of source."""
    policy = policy_for(template_id)
    organisations = {_organisation(item) for item in cited}
    met: list[str] = []
    unmet: list[SourceRequirement] = []
    for requirement in policy.requirements:
        carriers = {
            _organisation(item) for item in cited if characters_of(item) & requirement.characters
        }
        if len(carriers) >= requirement.minimum:
            met.append(requirement.id)
        else:
            unmet.append(requirement)
    return SourceSufficiency(
        template_id=template_id,
        organisations=len(organisations),
        minimum_organisations=policy.minimum_organisations,
        met=tuple(met),
        unmet=tuple(unmet),
    )


def describe_characters(item: EvidenceItem) -> str:
    """Plain wording for one item's character, for a review reason."""
    characters = sorted(characters_of(item))
    return ", ".join(CHARACTER_LABELS[character] for character in characters)
