"""Administrator-only operational aggregates. No source/user/provider payloads."""

from datetime import datetime

from pydantic import BaseModel

from ase.application.ports.worker_health import WorkerError


class WorkerHealthOut(BaseModel):
    name: str
    expected_interval_seconds: float
    last_cycle: datetime | None
    last_error_code: WorkerError | None
    overdue: bool


class RuntimeHealthOut(BaseModel):
    ready: bool
    workers: list[WorkerHealthOut]
    loop_lag_p99_ms: float
    bus_subscribers: int
    stream_drops: int
    bus_queue_depth: int
    read_rejections: int
    store_events: int
    store_bytes: int
    store_budget_bytes: int
    rss_bytes: int | None
    job_queue_depth: int
    stream_encoder_cached_chars: int
