"""Durable, lease-fenced reservations for every report generation provider request."""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from uuid import UUID, uuid4

from ase.application.ports.llm import LlmTokenBudgetExhausted
from ase.application.ports.web_search import WebSearchResult
from ase.application.report_jobs.budget_limits import (
    MAX_CALLS,
    MAX_COUNTER,
    MAX_OUTPUT_TOKENS,
    token_count,
)
from ase.application.report_jobs.fresh_web_allocation import check_web_discovery_dispatch
from ase.application.report_jobs.stage_budget import check_stage_budget
from ase.application.report_jobs.stage_reservations import ModelStage
from ase.domain.errors import InvalidRequest
from ase.domain.llm import LlmResult
from ase.domain.subscription_monthly_budget import MonthlyBudgetExhausted

__all__ = [
    "MAX_CALLS",
    "MAX_COUNTER",
    "MAX_OUTPUT_TOKENS",
    "JobBudgetExhausted",
    "JobInterrupted",
    "ReportCallBudget",
    "output_used",
    "token_count",
]

SETTLEMENT_TIMEOUT = 3.0
WEB_EXHAUSTED = "The model did not finish within its web-search output budget."

Payload = dict[str, Any]
MutatePayload = Callable[[Callable[[Payload], None]], Awaitable[Payload]]
CheckAccess = Callable[[], Awaitable[None]]
Result = TypeVar("Result", LlmResult, WebSearchResult)


class JobBudgetExhausted(InvalidRequest):
    code = "report_job_budget_exhausted"
    default_message = "This report has reached its lifetime call or output-token allowance."


class JobInterrupted(InvalidRequest):
    code = "report_job_interrupted"
    default_message = "Report generation stopped before its progress could be safely confirmed."


def _calls(payload: Payload) -> list[Payload]:
    calls = payload.setdefault("calls", [])
    if not isinstance(calls, list) or len(calls) > MAX_CALLS:
        raise JobInterrupted()
    for call in calls:
        if (
            not isinstance(call, dict)
            or call.get("status") not in {"in_flight", "completed", "failed", "uncertain"}
            or token_count(call.get("reserved_output")) is None
            or not 1 <= call["reserved_output"] <= MAX_OUTPUT_TOKENS
        ):
            raise JobInterrupted()
    return calls


def output_used(payload: Payload) -> int:
    """Output includes reasoning. Input tokens do not consume this output allowance."""
    total = 0
    for call in _calls(payload):
        known = token_count(call.get("completion_tokens"))
        total += (
            known
            if known is not None and call["status"] in {"completed", "failed"}
            else call["reserved_output"]
        )
    return total


def _observe_done(task: asyncio.Future[Payload]) -> None:
    if not task.cancelled():
        task.exception()


async def _save_once(mutate: MutatePayload, change: Callable[[Payload], None]) -> bool:
    """One writer only, including cancellation; never retry an uncertain commit."""
    pending = asyncio.ensure_future(mutate(change))
    deadline = time.monotonic() + SETTLEMENT_TIMEOUT
    try:
        async with asyncio.timeout(SETTLEMENT_TIMEOUT):
            await asyncio.shield(pending)
    except asyncio.CancelledError:
        try:
            async with asyncio.timeout(max(0, deadline - time.monotonic())):
                await asyncio.shield(pending)
        except (Exception, asyncio.CancelledError):
            pending.cancel()
            pending.add_done_callback(_observe_done)
        raise
    except Exception:
        pending.cancel()
        pending.add_done_callback(_observe_done)
        return False
    return True


class ReportCallBudget:
    """The supplied mutation atomically checks the job lease and persists its payload.

    The host records usage in that same transaction when an in-flight call settles.
    This component deliberately neither opens a database nor creates a second writer.
    """

    def __init__(
        self,
        mutate: MutatePayload,
        check: CheckAccess,
        *,
        profile_id: UUID | None = None,
        require_stage_plan: bool = False,
    ) -> None:
        self._mutate, self._check, self._profile_id = mutate, check, profile_id
        self._require_stage_plan = require_stage_plan

    def with_profile(self, profile_id: UUID) -> ReportCallBudget:
        """Attribute a call without creating another ledger or authorisation boundary."""
        return ReportCallBudget(
            self._mutate,
            self._check,
            profile_id=profile_id,
            require_stage_plan=self._require_stage_plan,
        )

    async def _reserve(
        self,
        request_hash: str,
        schema: str,
        model: str,
        reserved_output: int,
        stage: ModelStage | None,
    ) -> str:
        if (
            not re.fullmatch(r"[0-9a-f]{64}", request_hash)
            or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", schema)
            or not 1 <= len(model) <= 2048
            or any(ord(char) < 32 for char in model)
            or token_count(reserved_output) is None
            or not 1 <= reserved_output <= MAX_OUTPUT_TOKENS
        ):
            raise InvalidRequest("The report model request has invalid accounting metadata.")
        call_id = str(uuid4())

        def reserve(payload: Payload) -> None:
            calls = _calls(payload)
            exhausted = next(
                (
                    row
                    for row in calls
                    if row.get("request_hash") == request_hash
                    and row.get("error") == "token_budget_exhausted"
                ),
                None,
            )
            if exhausted is not None:
                raise LlmTokenBudgetExhausted(
                    model=model,
                    prompt_tokens=token_count(exhausted.get("prompt_tokens")),
                    completion_tokens=token_count(exhausted.get("completion_tokens")),
                )
            if (
                len(calls) >= MAX_CALLS
                or output_used(payload) + reserved_output > MAX_OUTPUT_TOKENS
            ):
                raise JobBudgetExhausted()
            if not check_web_discovery_dispatch(
                payload,
                calls,
                schema=schema,
                stage=stage,
                reserved_output=reserved_output,
            ):
                raise JobBudgetExhausted("The frozen fresh-web discovery allowance is exhausted.")
            stage_decision = check_stage_budget(
                payload, calls, stage, reserved_output, required=self._require_stage_plan
            )
            if stage_decision is not None and not stage_decision.allowed:
                raise JobBudgetExhausted(" ".join(stage_decision.reasons))
            calls.append(
                {
                    "id": call_id,
                    "status": "in_flight",
                    "request_hash": request_hash,
                    "schema": schema,
                    "model": model,
                    "profile_id": str(self._profile_id) if self._profile_id else None,
                    "reserved_output": reserved_output,
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "latency_ms": 0.0,
                    "error": None,
                    **({"stage": stage.value} if stage_decision is not None and stage else {}),
                }
            )

        try:
            await self._mutate(reserve)
        except (
            JobBudgetExhausted,
            JobInterrupted,
            LlmTokenBudgetExhausted,
            MonthlyBudgetExhausted,
        ):
            raise
        except Exception:
            raise JobInterrupted() from None
        return call_id

    async def run(
        self,
        *,
        request_hash: str,
        schema: str,
        model: str,
        reserved_output: int,
        invoke: Callable[[], Awaitable[Result]],
        stage: ModelStage | None = None,
    ) -> Result:
        await self._check()
        call_id = await self._reserve(request_hash, schema, model, reserved_output, stage)
        started = time.monotonic()
        cancelled = False
        final: Payload = {"status": "uncertain", "error": "interrupted"}
        try:
            # Reservation can wait for a concurrent mutation; recheck before sending data.
            await self._check()
            result = await invoke()
            failure = result.failure if isinstance(result, WebSearchResult) else None
            final = {
                "status": "failed" if failure else "completed",
                "error": (
                    "token_budget_exhausted"
                    if failure == WEB_EXHAUSTED
                    else "provider_error"
                    if failure
                    else None
                ),
                "prompt_tokens": token_count(result.prompt_tokens),
                "completion_tokens": token_count(result.completion_tokens),
            }
        except LlmTokenBudgetExhausted as exc:
            final = {
                "status": "failed",
                "error": "token_budget_exhausted",
                "prompt_tokens": token_count(exc.prompt_tokens),
                "completion_tokens": token_count(exc.completion_tokens),
            }
            raise
        except asyncio.CancelledError:
            cancelled = True
            raise
        except Exception:
            final = {"status": "failed", "error": "provider_error"}
            raise
        finally:
            final["latency_ms"] = round(max(0, time.monotonic() - started) * 1000, 3)

            def settle(payload: Payload) -> None:
                matches = [row for row in _calls(payload) if row.get("id") == call_id]
                if len(matches) != 1 or matches[0]["status"] != "in_flight":
                    raise JobInterrupted()
                matches[0].update(final)

            if not await _save_once(self._mutate, settle) and not cancelled:
                raise JobInterrupted() from None
        await self._check()
        return result
