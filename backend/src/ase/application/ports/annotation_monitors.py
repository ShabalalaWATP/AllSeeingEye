"""Atomic monitor persistence and immutable payload codecs."""

from typing import Protocol
from uuid import UUID

from ase.domain.access import Visibility
from ase.domain.annotation_comparison import AnnotationComparison
from ase.domain.annotation_monitoring import (
    AnnotationMonitor,
    AnnotationTransition,
    RevisionObservation,
)
from ase.domain.warning import Alert


class ComparisonCodec(Protocol):
    def decode(self, payload: bytes) -> AnnotationComparison: ...


class AnnotationMonitorRepository(Protocol):
    async def delete(self, monitor_id: UUID, expected_revision: int) -> bool: ...

    async def get(self, monitor_id: UUID) -> AnnotationMonitor | None: ...
    async def page(
        self,
        visibility: Visibility,
        report_id: UUID | None,
        number: int | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AnnotationMonitor], int]: ...
    async def usage(self, owner: UUID, team: UUID | None) -> tuple[int, int, int, int]: ...
    async def create(self, monitor: AnnotationMonitor, payload: bytes) -> None: ...
    async def checkpoint(self, monitor_id: UUID) -> bytes: ...
    async def save(self, value: AnnotationMonitor, expected_revision: int) -> bool: ...
    async def due(self, limit: int, after: UUID | None) -> list[UUID]: ...
    async def next_event(self, monitor_id: UUID) -> RevisionObservation | None: ...
    async def advance(
        self,
        value: AnnotationMonitor,
        expected_revision: int,
        transition: AnnotationTransition,
        payload: bytes,
        event_id: int | None,
        alert: Alert | None,
        reset: bool = False,
    ) -> bool: ...
    async def history(
        self, monitor_id: UUID, limit: int, offset: int
    ) -> tuple[list[AnnotationTransition], int]: ...
    async def transition(
        self, monitor_id: UUID, transition_id: UUID
    ) -> tuple[AnnotationTransition, bytes] | None: ...
