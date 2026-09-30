"""Conservative worker classification from saved, settled job checkpoints."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ase.domain.errors import RateLimited
from ase.domain.subscription_retry import RetryFailure


def _calls(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    value = payload.get("calls", [])
    if type(value) is not list or len(value) > 24 or any(type(row) is not dict for row in value):
        return None
    return value


def _running_sections(payload: dict[str, Any]) -> bool | None:
    sections = payload.get("sections", {})
    if type(sections) is not dict or any(type(value) is not dict for value in sections.values()):
        return None
    return any(value.get("status") == "running" for value in sections.values())


def classify_failure(
    error: BaseException,
    code: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> RetryFailure | None:
    """A retryable transport error must be proven to precede a new paid reservation."""
    before_calls, after_calls = _calls(before), _calls(after)
    if before_calls is None or after_calls is None:
        return None
    failure = {
        "budget_exhausted": RetryFailure.JOB_BUDGET,
        "monthly_budget_exhausted": RetryFailure.MONTHLY_BUDGET,
        "access_changed": RetryFailure.SCOPE_REVOKED,
        "model_changed": RetryFailure.CAPABILITY_MISSING,
        "source_disabled": RetryFailure.SCOPE_REVOKED,
    }.get(code)
    if any(row.get("status") in {"in_flight", "uncertain"} for row in after_calls):
        failure = RetryFailure.UNCERTAIN_PAID_CALL
    elif (
        failure is None
        and not any(row.get("error") in {"provider_error", "interrupted"} for row in after_calls)
        and before_calls == after_calls
        and _running_sections(before) is False
    ):
        if isinstance(error, RateLimited):
            failure = RetryFailure.RETRYABLE_RESPONSE
        elif isinstance(error, ConnectionError):
            failure = RetryFailure.TRANSIENT_PRE_DISPATCH
    return failure


def automatic_retry_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Reset only a pre-dispatch running section; completed checkpoints remain intact."""
    calls = _calls(payload)
    if calls is None or any(
        row.get("status") not in {"completed", "failed"}
        or row.get("error") in {"provider_error", "interrupted"}
        for row in calls
    ):
        return None
    if _running_sections(payload) is None:
        return None
    copied = deepcopy(payload)
    for section in copied.get("sections", {}).values():
        if section.get("status") == "running":
            section["status"] = "incomplete"
            section["reason"] = "known_transient_failure"
    return copied
