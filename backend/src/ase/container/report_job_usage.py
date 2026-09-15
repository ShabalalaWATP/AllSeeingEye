"""Account only immutable, lease-fenced transitions of an existing call reservation."""

import math
from datetime import datetime
from typing import Any
from uuid import UUID

from ase.application.report_jobs.budget import MAX_CALLS, JobInterrupted, token_count
from ase.domain.llm import LlmUsage
from ase.domain.subscription_monthly_budget import utc_month

_MUTABLE = frozenset({"status", "prompt_tokens", "completion_tokens", "latency_ms", "error"})


def _calls(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = payload.get("calls", [])
    if type(values) is not list or len(values) > MAX_CALLS:
        raise JobInterrupted()
    found = {}
    for value in values:
        if type(value) is not dict or type(value.get("id")) is not str:
            raise JobInterrupted()
        try:
            if str(UUID(value["id"])) != value["id"]:
                raise ValueError
            UUID(value["profile_id"])
        except (ValueError, TypeError, KeyError, AttributeError):
            raise JobInterrupted() from None
        if value["id"] in found or value.get("status") not in {
            "in_flight",
            "completed",
            "failed",
            "uncertain",
        }:
            raise JobInterrupted()
        found[value["id"]] = value
    return found


def settled_usage(
    before: dict[str, Any], after: dict[str, Any], owner_id: UUID, now: datetime
) -> list[LlmUsage]:
    old, new = _calls(before), _calls(after)
    if list(new)[: len(old)] != list(old):
        raise JobInterrupted()
    result = []
    for key, value in new.items():
        previous = old.get(key)
        if previous is None:
            if value["status"] != "in_flight":
                raise JobInterrupted()
            continue
        if previous == value:
            continue
        if previous["status"] != "in_flight" or value["status"] == "in_flight":
            raise JobInterrupted()
        if {k: v for k, v in previous.items() if k not in _MUTABLE} != {
            k: v for k, v in value.items() if k not in _MUTABLE
        }:
            raise JobInterrupted()
        if value["status"] == "uncertain":
            continue
        latency = value.get("latency_ms")
        error = value.get("error")
        if not isinstance(latency, (int, float)) or isinstance(latency, bool):
            raise JobInterrupted()
        if (
            not math.isfinite(latency)
            or not 0 <= latency <= 3_600_000
            or error not in {None, "provider_error", "token_budget_exhausted", "interrupted"}
            or (value["status"] == "completed" and error is not None)
        ):
            raise JobInterrupted()
        dispatched_at = previous.get("dispatched_at", now.isoformat())
        if type(dispatched_at) is not str or len(dispatched_at) > 40:
            raise JobInterrupted()
        try:
            at = datetime.fromisoformat(dispatched_at)
            utc_month(at)
        except ValueError:
            raise JobInterrupted() from None
        result.append(
            LlmUsage(
                at=at,
                profile_id=UUID(value["profile_id"]),
                user_id=owner_id,
                purpose="report-job",
                ok=value["status"] == "completed",
                latency_ms=float(latency),
                prompt_tokens=token_count(value.get("prompt_tokens")),
                completion_tokens=token_count(value.get("completion_tokens")),
                error=error,
            )
        )
    return result
