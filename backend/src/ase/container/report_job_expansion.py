"""Lease-fenced E05 task-plan and packet checkpoints for report jobs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from ase.application.report_jobs.budget import JobInterrupted
from ase.application.reports.challenge_expansion_checkpoint import (
    ExpansionPacket,
    ExpansionPlan,
    packet_from_dict,
    packet_to_dict,
    plan_from_dict,
    plan_to_dict,
    validate_lineage,
)
from ase.application.reports.challenge_expansion_partial import (
    KEY,
    PartialResult,
    decode_partial,
    encode_partial,
)
from ase.application.reports.production_checkpoint import collection_from_dict
from ase.application.research.phase_ledger import LEDGER_KEY, SettlementReceipt, settle_operation
from ase.application.research.reserved_collection import source_item_key
from ase.domain.evidence import EvidenceItem
from ase.domain.research import CollectionAttempt, ResearchMode
from ase.domain.research_records import ResearchReceipt


class ChallengeExpansionMixin:
    async def _read(self) -> dict[str, Any]:
        raise NotImplementedError

    async def mutate(self, callback: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        raise NotImplementedError

    async def load_expansion_plan(self) -> ExpansionPlan | None:
        value = (await self._read()).get("challenge_expansion_plan")
        return plan_from_dict(value) if value is not None else None

    async def load_challenge_partial(
        self,
    ) -> tuple[tuple[EvidenceItem, ...], tuple[CollectionAttempt, ...]]:
        payload = await self._read()
        saved = payload.get("challenge_expansion_plan")
        if saved is None:
            return (), ()
        plan = plan_from_dict(saved)
        rows = decode_partial(payload.get(KEY), plan.fingerprint)
        return (
            tuple(item for row in rows for item in row.evidence),
            tuple(row.attempt for row in rows),
        )

    async def settle_challenge_operation(
        self,
        *,
        mode: ResearchMode,
        request_key: str,
        elapsed_ms: int,
        evidence: tuple[EvidenceItem, ...],
        attempt: CollectionAttempt,
    ) -> SettlementReceipt:
        """Commit accepted frozen excerpts and source charge atomically."""
        captured: list[SettlementReceipt] = []

        def settle(payload: dict[str, Any]) -> None:
            if LEDGER_KEY not in payload or "collection" not in payload:
                raise JobInterrupted()
            plan = plan_from_dict(payload.get("challenge_expansion_plan"))
            snapshot = collection_from_dict(payload["collection"])
            if plan.status != "ready" or snapshot.query is None or snapshot.query.mode != mode:
                raise JobInterrupted()
            old = decode_partial(payload.get(KEY), plan.fingerprint)
            if any(row.request_key == request_key for row in old):
                raise JobInterrupted()
            receipt = settle_operation(
                payload,
                mode=mode,
                phase="challenge",
                request_key=request_key,
                elapsed_ms=elapsed_ms,
                retained_item_keys=tuple(source_item_key(item.event_id) for item in evidence),
            )
            accepted = set(receipt.retained_keys)
            original = snapshot.selection.items
            current = tuple(item for row in old for item in row.evidence)
            first = (
                max(
                    (
                        int(item.label[1:])
                        for item in (*original, *current)
                        if item.label[1:].isdigit()
                    ),
                    default=0,
                )
                + 1
            )
            fresh = tuple(
                replace(item, label=f"E{first + index}")
                for index, item in enumerate(
                    item for item in evidence if source_item_key(item.event_id) in accepted
                )
            )
            safe_attempt = replace(
                attempt,
                result_count=len(fresh),
                explanation=attempt.explanation[:1000],
            )
            rows = (*old, PartialResult(request_key, fresh, safe_attempt))
            combined = tuple(item for row in rows for item in row.evidence)
            trial = ExpansionPacket(
                plan.parent,
                plan.fingerprint,
                combined,
                ResearchReceipt.build(
                    snapshot.query,
                    tuple(row.attempt for row in rows),
                    len(combined),
                ),
                "attempted",
                "Fresh source requests were attempted.",
            )
            validate_lineage(trial, plan, snapshot)
            payload[KEY] = encode_partial(rows, plan.fingerprint)
            captured.append(receipt)

        await self.mutate(settle)
        return captured[0]

    async def save_expansion_plan(self, plan: ExpansionPlan) -> None:
        value = plan_to_dict(plan)

        def save(payload: dict[str, Any]) -> None:
            old = payload.get("challenge_expansion_plan")
            if old is not None and old != value:
                raise JobInterrupted()
            payload["challenge_expansion_plan"] = value
            payload["stage"] = "challenging"

        await self.mutate(save)

    async def load_expansion_packet(self) -> ExpansionPacket | None:
        value = (await self._read()).get("challenge_expansion_packet")
        return packet_from_dict(value) if value is not None else None

    async def save_expansion_packet(self, packet: ExpansionPacket) -> None:
        value = packet_to_dict(packet)

        def save(payload: dict[str, Any]) -> None:
            saved = payload.get("challenge_expansion_plan")
            if saved is None:
                raise JobInterrupted()
            plan = plan_from_dict(saved)
            if packet.parent != plan.parent or packet.plan_fingerprint != plan.fingerprint:
                raise JobInterrupted()
            partial = decode_partial(payload.get(KEY), plan.fingerprint)
            selected = tuple(item for row in partial for item in row.evidence)
            if partial and packet.added != selected:
                raise JobInterrupted()
            old = payload.get("challenge_expansion_packet")
            if old is not None and old != value:
                raise JobInterrupted()
            payload["challenge_expansion_packet"] = value
            payload["stage"] = "drafting"

        await self.mutate(save)
