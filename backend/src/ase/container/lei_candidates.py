"""Name lookup shares source controls and the existing bounded public HTTP client."""

from ase.adapters.research_records.gleif_candidates import GleifCandidates
from ase.application.research.lei_candidates import FindLeiCandidates
from ase.container.core import ContainerCore


def lei_candidates(container: ContainerCore) -> FindLeiCandidates:
    return FindLeiCandidates(
        GleifCandidates(container.http),
        container.limiter,
        container.source_admission,
    )
