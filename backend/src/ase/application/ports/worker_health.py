"""Progress observation is separate from source/provider success."""

from typing import Literal, Protocol

WorkerError = Literal["cycle_failed"]


class WorkerHeartbeats(Protocol):
    def register(self, name: str, expected_interval: float) -> None: ...

    def completed(
        self, name: str, expected_interval: float, error_code: WorkerError | None = None
    ) -> None: ...
