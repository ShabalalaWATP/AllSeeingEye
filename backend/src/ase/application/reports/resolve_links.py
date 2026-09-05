"""Resolve links only after a report has chosen which frozen evidence it cites."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence, Set
from dataclasses import replace

from ase.application.ports.evidence_urls import EvidenceUrlResolver
from ase.domain.evidence import EvidenceItem

MAX_RESOLVED_LINKS = 30
RESOLUTION_BUDGET_SECONDS = 10.0


async def resolve_cited_links(
    resolver: EvidenceUrlResolver,
    evidence: Sequence[EvidenceItem],
    cited_labels: Set[str],
) -> tuple[EvidenceItem, ...]:
    """Retain frozen content and original links when resolution fails; never fetch uncited items."""
    resolved: dict[str, str | None] = {}
    result: list[EvidenceItem] = []
    deadline = asyncio.get_running_loop().time() + RESOLUTION_BUDGET_SECONDS
    for item in evidence:
        updated = item
        if item.label in cited_labels and item.url:
            remaining = deadline - asyncio.get_running_loop().time()
            if item.url not in resolved and len(resolved) < MAX_RESOLVED_LINKS and remaining > 0:
                try:
                    async with asyncio.timeout(min(5, remaining)):
                        resolved[item.url] = await resolver.resolve(item.url)
                except Exception:
                    resolved[item.url] = None
            target = resolved.get(item.url)
            if target:
                updated = replace(item, url=target)
        result.append(updated)
    return tuple(result)
