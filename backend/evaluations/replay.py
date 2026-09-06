"""Scripted provider packets exercising production collection, never live retrieval."""

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.application.research.service import ResearchCollectionService
from ase.domain.events import Event
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchQuery,
)

if TYPE_CHECKING:
    from evaluations.casebook import EvaluationCase


class ReplayPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(default="Synthetic replay provider", min_length=1, max_length=120)
    event_keys: list[str] = Field(default_factory=list, max_length=50)
    status: Literal["completed", "empty", "unavailable", "failed"] = "completed"

    @model_validator(mode="after")
    def consistent_status(self) -> "ReplayPacket":
        if len(set(self.event_keys)) != len(self.event_keys):
            raise ValueError("Replay event keys must be unique within a packet.")
        if self.event_keys and self.status != "completed":
            raise ValueError("Only completed replay packets may contain events.")
        return self


class ReplayScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    initial: list[ReplayPacket] = Field(min_length=1, max_length=64)
    challenge: list[ReplayPacket] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def unique_providers(self) -> "ReplayScenario":
        for packets in (self.initial, self.challenge):
            if len({packet.id for packet in packets}) != len(packets):
                raise ValueError("Replay provider ids must be unique within each stage.")
        return self


class ReplayProvider:
    def __init__(
        self,
        packet: ReplayPacket,
        events: tuple[Event, ...],
        stage: str,
        calls: list[dict[str, Any]],
    ) -> None:
        self.id, self.name = packet.id, packet.name
        self.packet, self.events = packet, events
        self.stage, self.calls = stage, calls

    def supports(self, query: ResearchQuery) -> bool:
        return True

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        self.calls.append(
            {
                "stage": self.stage,
                "provider_id": self.id,
                "terms": list(query.terms),
                "languages": list(query.languages),
                "since": query.since.isoformat(),
                "until": query.until.isoformat(),
                "returned_event_ids": [event.id for event in self.events],
            }
        )
        return ResearchBatch(
            items=self.events,
            attempts=(
                CollectionAttempt(
                    self.id,
                    self.name,
                    CollectionStatus(self.packet.status),
                    len(self.events),
                    "Synthetic replay packet; returned independently of search terms. "
                    "This does not measure live retrieval or search relevance.",
                ),
            ),
        )


class ResearchReplay:
    def __init__(self, case: "EvaluationCase") -> None:
        if case.replay is None:
            raise ValueError("Research evaluation requires an explicit case replay scenario.")
        self.calls: list[dict[str, Any]] = []
        events = case.graded_events()

        def providers(packets: list[ReplayPacket], stage: str) -> tuple[ReplayProvider, ...]:
            return tuple(
                ReplayProvider(
                    packet,
                    tuple(
                        event for event in events if event.id in case.event_ids(packet.event_keys)
                    ),
                    stage,
                    self.calls,
                )
                for packet in packets
            )

        initial = providers(case.replay.initial, "initial")
        challenge = providers(case.replay.challenge, "challenge")
        self.collection = ResearchCollectionService(
            lambda query: initial,
            challenge_providers=lambda query: challenge,
        )

    def result(self) -> dict[str, Any]:
        return {
            "kind": "synthetic_provider_replay",
            "live_retrieval_evaluated": False,
            "query_relevance_evaluated": False,
            "provider_calls": self.calls,
        }
