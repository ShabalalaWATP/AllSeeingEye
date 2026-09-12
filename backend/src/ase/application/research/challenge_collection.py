"""Round-robin counterevidence requests share one budget across all judgements."""

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import replace

from ase.application.ports.research import ResearchProvider
from ase.application.research.collection import CollectionBudget, ResearchCollector
from ase.domain.events import Event
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchMode,
    ResearchQuery,
)

MAX_CHALLENGE_QUERIES = 32


async def collect_challenges(
    queries: tuple[ResearchQuery, ...],
    providers: Callable[[ResearchQuery], Sequence[ResearchProvider]],
) -> tuple[ResearchBatch, ...]:
    if len(queries) > MAX_CHALLENGE_QUERIES:
        raise ValueError("Too many judgement challenge queries")
    advanced = bool(queries) and all(query.mode is ResearchMode.ADVANCED for query in queries)
    request_limit, item_limit, seconds = (12, 400, 90) if advanced else (6, 200, 45)
    selected = [tuple(providers(query)) for query in queries]
    # Validate provider inventories before starting any external work.
    for inventory in selected:
        ResearchCollector(inventory)
    attempts: list[list[CollectionAttempt]] = [[] for _ in queries]
    items: list[dict[str, Event]] = [{} for _ in queries]
    unique: set[str] = set()
    requests = 0
    deadline = asyncio.get_running_loop().time() + seconds
    allocation = max(1, item_limit // min(len(queries) or 1, request_limit))
    for turn in range(max((len(inventory) for inventory in selected), default=0)):
        for index, (query, inventory) in enumerate(zip(queries, selected, strict=True)):
            if turn >= len(inventory):
                continue
            provider = inventory[turn]
            remaining = deadline - asyncio.get_running_loop().time()
            if not provider.supports(query):
                attempts[index].append(
                    CollectionAttempt(
                        provider.id,
                        provider.name,
                        CollectionStatus.UNSUPPORTED,
                        explanation="This source does not support this challenge query.",
                    )
                )
                continue
            if requests >= request_limit or remaining <= 0 or len(unique) >= item_limit:
                attempts[index].append(
                    CollectionAttempt(
                        provider.id,
                        provider.name,
                        CollectionStatus.BUDGET_EXHAUSTED,
                        explanation=f"The shared {request_limit}-request challenge budget "
                        "was reached. "
                        "This does not confirm the judgement.",
                    )
                )
                continue
            requests += 1
            batch = await ResearchCollector([provider]).collect(
                replace(query, source_ids=(provider.id,)),
                budget=CollectionBudget(
                    requests=1,
                    seconds=remaining,
                    per_request_seconds=min(12, remaining),
                    items=min(allocation, item_limit - len(unique)),
                ),
            )
            attempts[index].extend(batch.attempts)
            items[index].update((item.id, item) for item in batch.items)
            unique.update(item.id for item in batch.items)
    return tuple(
        ResearchBatch(tuple(pool.values()), tuple(receipts))
        for pool, receipts in zip(items, attempts, strict=True)
    )
