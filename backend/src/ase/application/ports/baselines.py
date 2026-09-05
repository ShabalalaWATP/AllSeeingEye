"""Ports for the tiny hourly aggregates that give warning rules their "normal levels"."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol


class BaselineRepository(Protocol):
    """Hourly samples per kind and key; a repeat sample in the same hour keeps the larger."""

    async def record(self, kind: str, key: str, hour: datetime, value: int) -> None: ...

    async def means(self, kind: str, since: datetime) -> Mapping[str, float]:
        """Mean hourly value per key over the samples since the given time."""
        ...


class BaselineSink(Protocol):
    """Where a background sampler writes, without knowing about database sessions."""

    async def record_many(
        self, hour: datetime, samples: Sequence[tuple[str, str, int]]
    ) -> None: ...
