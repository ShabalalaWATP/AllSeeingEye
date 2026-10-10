"""Source identities whose retained content contributes to an evidence record."""

from collections.abc import Iterable

from ase.domain.evidence import EvidenceItem


def evidence_source_ids(evidence: Iterable[EvidenceItem]) -> set[str]:
    """Folding keeps other sources' provenance, so their admission still applies."""
    identifiers: set[str] = set()
    for item in evidence:
        identifiers.add(item.source_id)
        identifiers.update(member.source_id for member in item.corroboration)
    return identifiers
