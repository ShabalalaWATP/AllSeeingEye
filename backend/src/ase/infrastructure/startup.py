"""Bounded, non-sensitive duration evidence for cold-start phases."""

from time import perf_counter

import structlog

log = structlog.get_logger(__name__)


def record_startup_phase(phase: str, started: float) -> None:
    log.info("startup.phase", phase=phase, duration_ms=round((perf_counter() - started) * 1000, 3))
