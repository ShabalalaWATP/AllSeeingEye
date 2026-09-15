"""Durable, serial source-phase allowances for checkpointed acquisition.

Call these pure payload mutations inside a lease-fenced checkpoint transaction.
Only integer elapsed milliseconds are persisted, never a process-local clock.
An open operation reserves its entire request deadline until it is settled or
explicitly abandoned after an interrupted worker has been fenced out.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, cast

from ase.application.research.source_allocation_types import DEPTH_CAPS
from ase.domain.research import ResearchMode

LEDGER_KEY = "source_phase_ledger"
LEDGER_VERSION = 1
Phase = Literal["initial", "challenge"]


class PhaseLedgerError(ValueError):
    """A malformed snapshot, conflicting replay or exhausted phase allowance."""


@dataclass(frozen=True, slots=True)
class ReservationDecision:
    status: str
    dispatch: bool
    allowance_ms: int
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SettlementReceipt:
    charged_ms: int
    retained_keys: tuple[str, ...]
    excluded_keys: tuple[str, ...]


def _limits(mode: ResearchMode) -> dict[str, dict[str, int]]:
    if not isinstance(mode, ResearchMode):
        raise PhaseLedgerError("Unknown research depth")
    total, challenge, initial_seconds, challenge_seconds, initial_items, challenge_items = (
        DEPTH_CAPS[mode]
    )
    request_ms = 12_000 if mode is ResearchMode.QUICK else 20_000
    return {
        "initial": {
            "operations": total - challenge,
            "active_ms": initial_seconds * 1_000,
            "items": initial_items,
            "per_request_ms": request_ms,
        },
        "challenge": {
            "operations": challenge,
            "active_ms": challenge_seconds * 1_000,
            "items": challenge_items,
            "per_request_ms": request_ms if challenge else 0,
        },
    }


def new_phase_ledger(mode: ResearchMode) -> dict[str, Any]:
    """Make a JSON-safe v1 snapshot with policy limits frozen for this depth."""
    return {
        "version": LEDGER_VERSION,
        "mode": mode.value,
        "phases": {
            name: {"limits": limits, "operations": {}} for name, limits in _limits(mode).items()
        },
    }


def _key(value: object, *, maximum: int) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= maximum
        and value == value.strip()
        and not any(ord(character) < 32 for character in value)
    )


def _keys(values: object) -> bool:
    return (
        type(values) is list
        and len(values) <= 1_000
        and all(_key(value, maximum=256) for value in values)
        and len(values) == len(set(values))
    )


def _valid_operation(operation: object, limits: dict[str, int]) -> bool:
    if type(operation) is not dict or set(operation) != {
        "status",
        "allowance_ms",
        "charged_ms",
        "elapsed_ms",
        "offered_keys",
        "retained_keys",
    }:
        return False
    allowance = operation["allowance_ms"]
    charged = operation["charged_ms"]
    elapsed = operation["elapsed_ms"]
    status = operation["status"]
    if (
        type(status) is not str
        or type(allowance) is not int
        or not 1 <= allowance <= limits["per_request_ms"]
        or type(charged) is not int
        or charged < 0
        or not _keys(operation["offered_keys"])
        or not _keys(operation["retained_keys"])
    ):
        return False
    offered = operation["offered_keys"]
    retained = operation["retained_keys"]
    if status in {"open", "unknown"}:
        return charged == allowance and elapsed is None and not offered and not retained
    return (
        status == "settled"
        and type(elapsed) is int
        and 0 <= elapsed <= allowance
        and charged == elapsed
        and set(retained) <= set(offered)
    )


def _validated(payload: dict[str, Any], mode: ResearchMode) -> dict[str, Any]:
    ledger = deepcopy(payload.get(LEDGER_KEY)) if LEDGER_KEY in payload else new_phase_ledger(mode)
    limits_by_phase = _limits(mode)
    if (
        type(ledger) is not dict
        or set(ledger) != {"version", "mode", "phases"}
        or type(ledger["version"]) is not int
        or ledger["version"] != LEDGER_VERSION
        or ledger["mode"] != mode.value
        or type(ledger["phases"]) is not dict
        or set(ledger["phases"]) != set(limits_by_phase)
    ):
        raise PhaseLedgerError("Invalid source-phase ledger version or depth")
    all_retained: set[str] = set()
    for name, expected_limits in limits_by_phase.items():
        phase = ledger["phases"][name]
        if type(phase) is not dict or set(phase) != {"limits", "operations"}:
            raise PhaseLedgerError("Invalid source-phase ledger shape")
        limits, operations = phase["limits"], phase["operations"]
        if (
            type(limits) is not dict
            or limits != expected_limits
            or any(type(value) is not int for value in limits.values())
            or type(operations) is not dict
            or len(operations) > limits["operations"]
            or any(
                not _key(key, maximum=160) or not _valid_operation(value, limits)
                for key, value in operations.items()
            )
            or sum(value["status"] == "open" for value in operations.values()) > 1
        ):
            raise PhaseLedgerError("Invalid source-phase operation or policy limits")
        retained = [key for value in operations.values() for key in value["retained_keys"]]
        if (
            len(retained) > limits["items"]
            or len(retained) != len(set(retained))
            or any(key in all_retained for key in retained)
            or _usage(phase)[1] > limits["active_ms"]
        ):
            raise PhaseLedgerError("Invalid or duplicate retained source item")
        all_retained.update(retained)
    return cast("dict[str, Any]", ledger)


def _phase(ledger: dict[str, Any], phase: Phase) -> dict[str, Any]:
    if phase not in ("initial", "challenge"):
        raise PhaseLedgerError("Unknown source acquisition phase")
    return cast("dict[str, Any]", ledger["phases"][phase])


def _usage(phase: dict[str, Any]) -> tuple[int, int, int]:
    operations = phase["operations"]
    return (
        len(operations),
        sum(operation["charged_ms"] for operation in operations.values()),
        sum(len(operation["retained_keys"]) for operation in operations.values()),
    )


def operation_count_with_prefix(
    payload: dict[str, Any], *, mode: ResearchMode, phase: Phase, prefix: str
) -> int:
    """Count admitted attempts, including unknown ones, before another reservation."""
    if not _key(prefix, maximum=80):
        raise PhaseLedgerError("Invalid source operation prefix")
    operations = _phase(_validated(payload, mode), phase)["operations"]
    return sum(key.startswith(prefix) for key in operations)


def reserve_operation(
    payload: dict[str, Any], *, mode: ResearchMode, phase: Phase, request_key: str
) -> ReservationDecision:
    """Reserve before dispatch; only a newly recorded key permits outbound work."""
    if not _key(request_key, maximum=160):
        raise PhaseLedgerError("Invalid source operation key")
    ledger = _validated(payload, mode)
    record = _phase(ledger, phase)
    limits, operations = record["limits"], record["operations"]
    if request_key in operations:
        existing = operations[request_key]
        return ReservationDecision(existing["status"], False, existing["allowance_ms"], "replayed")
    used_operations, used_ms, used_items = _usage(record)
    reason = next(
        (
            reason
            for denied, reason in (
                (any(op["status"] == "open" for op in operations.values()), "operation_open"),
                (used_operations >= limits["operations"], "operation_cap"),
                (used_items >= limits["items"], "item_cap"),
                (used_ms >= limits["active_ms"], "time_cap"),
            )
            if denied
        ),
        None,
    )
    if reason is not None:
        payload[LEDGER_KEY] = ledger
        return ReservationDecision("denied", False, 0, reason)
    allowance = min(limits["per_request_ms"], limits["active_ms"] - used_ms)
    operations[request_key] = {
        "status": "open",
        "allowance_ms": allowance,
        "charged_ms": allowance,
        "elapsed_ms": None,
        "offered_keys": [],
        "retained_keys": [],
    }
    payload[LEDGER_KEY] = ledger
    return ReservationDecision("open", True, allowance)


def settle_operation(
    payload: dict[str, Any],
    *,
    mode: ResearchMode,
    phase: Phase,
    request_key: str,
    elapsed_ms: int,
    retained_item_keys: tuple[str, ...] | list[str],
) -> SettlementReceipt:
    """Settle known elapsed time and admit only globally new retained keys."""
    if (
        not _key(request_key, maximum=160)
        or type(elapsed_ms) is not int
        or not 0 <= elapsed_ms <= 2_147_483_647
        or type(retained_item_keys) not in (tuple, list)
        or len(retained_item_keys) > 1_000
        or any(not _key(key, maximum=256) for key in retained_item_keys)
    ):
        raise PhaseLedgerError("Invalid source settlement")
    offered = tuple(dict.fromkeys(retained_item_keys))
    ledger = _validated(payload, mode)
    record = _phase(ledger, phase)
    operation = record["operations"].get(request_key)
    if operation is None or operation["status"] == "unknown":
        raise PhaseLedgerError("Source operation is absent or conservatively abandoned")
    if operation["status"] == "settled":
        if operation["elapsed_ms"] != elapsed_ms or operation["offered_keys"] != list(offered):
            raise PhaseLedgerError("Conflicting source operation settlement")
    else:
        if elapsed_ms > operation["allowance_ms"]:
            raise PhaseLedgerError("Source operation exceeded its reserved deadline")
        existing = {
            key
            for phase_record in ledger["phases"].values()
            for row in phase_record["operations"].values()
            for key in row["retained_keys"]
        }
        available = record["limits"]["items"] - _usage(record)[2]
        retained: list[str] = []
        for key in offered:
            if key not in existing and len(retained) < available:
                retained.append(key)
                existing.add(key)
        operation.update(
            {
                "status": "settled",
                "charged_ms": elapsed_ms,
                "elapsed_ms": elapsed_ms,
                "offered_keys": list(offered),
                "retained_keys": retained,
            }
        )
        payload[LEDGER_KEY] = ledger
    accepted = tuple(operation["retained_keys"])
    return SettlementReceipt(
        elapsed_ms, accepted, tuple(key for key in offered if key not in accepted)
    )


def abandon_operation(
    payload: dict[str, Any], *, mode: ResearchMode, phase: Phase, request_key: str
) -> ReservationDecision:
    """Fence an interrupted open request without refunding its time or operation."""
    if not _key(request_key, maximum=160):
        raise PhaseLedgerError("Invalid source operation key")
    ledger = _validated(payload, mode)
    operation = _phase(ledger, phase)["operations"].get(request_key)
    if operation is None:
        raise PhaseLedgerError("Source operation is absent")
    if operation["status"] == "open":
        operation["status"] = "unknown"
        payload[LEDGER_KEY] = ledger
    return ReservationDecision(operation["status"], False, operation["allowance_ms"])
