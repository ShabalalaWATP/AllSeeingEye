"""Storage boundary for the small cached economy explainer aggregate."""

from typing import Protocol

from ase.domain.economy_explainer import StoredExplainer


class EconomyExplainerRepository(Protocol):
    async def latest(self) -> StoredExplainer | None: ...

    async def save(self, explainer: StoredExplainer) -> None:
        """Store one generated explainer and keep only the newest retained rows."""
        ...
