"""The separate challenge phase cannot consume or replay initial allowances."""

from dataclasses import replace

import pytest

from ase.application.research.phase_ledger import LEDGER_KEY, new_phase_ledger, settle_operation
from ase.application.research.reserved_collection import source_item_key
from ase.application.research.service import ResearchCollectionService
from ase.domain.evidence import EvidenceItem
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch, ResearchMode
from test_research_collection import QUERY, Provider, event
from test_reserved_collection import MemoryOperations


class MemoryChallengeOperations(MemoryOperations):
    def __init__(self, payload):
        super().__init__(payload)
        self.evidence: tuple[EvidenceItem, ...] = ()
        self.attempts: tuple[CollectionAttempt, ...] = ()

    async def load_challenge_partial(self):
        return self.evidence, self.attempts

    async def settle_challenge_operation(self, *, mode, request_key, elapsed_ms, evidence, attempt):
        settled = settle_operation(
            self.payload,
            mode=mode,
            phase="challenge",
            request_key=request_key,
            elapsed_ms=elapsed_ms,
            retained_item_keys=tuple(source_item_key(item.event_id) for item in evidence),
        )
        self.evidence += tuple(
            item for item in evidence if source_item_key(item.event_id) in settled.retained_keys
        )
        self.attempts += (attempt,)
        return settled


async def freeze(batch):
    return tuple(
        EvidenceItem.from_event(
            f"E{index}", item, QUERY.until, source_name=item.source_id, independence_key=""
        )
        for index, item in enumerate(batch.items, start=1)
    )


async def test_deep_pass_uses_only_reserved_challenge_operations() -> None:
    query = replace(QUERY, mode=ResearchMode.DETAILED, terms=("disprove",))
    providers = [
        Provider(f"source-{index}", ResearchBatch(items=(event(f"item-{index}"),)))
        for index in range(7)
    ]
    service = ResearchCollectionService(lambda _: providers)
    operations = MemoryChallengeOperations({LEDGER_KEY: new_phase_ledger(query.mode)})
    frozen_ids = service.plan_challenge(query)
    assert frozen_ids == tuple(row.id for row in providers[:4])
    batch = await service.collect_challenge_checkpointed(query, frozen_ids, operations, freeze)
    assert len(batch.items) == 4
    assert [row.called for row in providers] == [1, 1, 1, 1, 0, 0, 0]
    ledger = operations.payload[LEDGER_KEY]["phases"]
    assert ledger["initial"]["operations"] == {}
    assert len(ledger["challenge"]["operations"]) == 4
    assert all(key.startswith("challenge:") for key in ledger["challenge"]["operations"])

    resumed = await service.collect_challenge_checkpointed(query, frozen_ids, operations, freeze)
    assert resumed.items == ()
    assert all(row.status is CollectionStatus.NOT_COLLECTED for row in resumed.attempts)
    assert [row.called for row in providers] == [1, 1, 1, 1, 0, 0, 0]


async def test_changed_provider_inventory_is_rejected_before_network() -> None:
    query = replace(QUERY, mode=ResearchMode.ADVANCED, terms=("disprove",))
    provider = Provider("first")
    service = ResearchCollectionService(lambda _: (provider,))
    operations = MemoryChallengeOperations({LEDGER_KEY: new_phase_ledger(query.mode)})
    with pytest.raises(ValueError, match="frozen challenge"):
        await service.collect_challenge_checkpointed(query, ("invented",), operations, freeze)
    assert provider.called == 0
    assert operations.payload[LEDGER_KEY]["phases"]["challenge"]["operations"] == {}
