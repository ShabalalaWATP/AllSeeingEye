"""Cumulative known report usage, including work retained from earlier attempts."""

from typing import Any

from ase.application.report_jobs.budget import token_count
from ase.domain.report_records import ReportVersion


def apply_usage(version: ReportVersion, payload: dict[str, Any]) -> None:
    calls = payload.get("calls", [])

    def total(key: str) -> int | None:
        values = [token_count(row.get(key)) for row in calls]
        return (
            sum(value for value in values if value is not None)
            if all(value is not None for value in values)
            and all(row.get("status") in {"completed", "failed"} for row in calls)
            else None
        )

    version.prompt_tokens = total("prompt_tokens")
    version.completion_tokens = total("completion_tokens")
    version.latency_ms = sum(float(row.get("latency_ms", 0)) for row in calls)
