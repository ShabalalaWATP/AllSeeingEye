"""Fence open source requests from an earlier job lease without refunding them."""

from __future__ import annotations

from typing import Any

from ase.application.research.phase_ledger import (
    LEDGER_KEY,
    Phase,
    PhaseLedgerError,
    abandon_operation,
)
from ase.domain.research import ResearchMode


def reconcile_open_operations(payload: dict[str, Any], mode: ResearchMode) -> bool:
    """Return whether this job has a ledger; prior open calls become unknown."""
    ledger = payload.get(LEDGER_KEY)
    if ledger is None:
        return False  # Jobs queued before this policy retain their original path.
    if type(ledger) is not dict or type(ledger.get("phases")) is not dict:
        raise PhaseLedgerError("Invalid source-phase ledger shape")
    phases: tuple[Phase, Phase] = ("initial", "challenge")
    for phase in phases:
        row = ledger["phases"].get(phase)
        if type(row) is not dict or type(row.get("operations")) is not dict:
            raise PhaseLedgerError("Invalid source-phase ledger shape")
        for key, operation in tuple(row["operations"].items()):
            if type(operation) is dict and operation.get("status") == "open":
                abandon_operation(payload, mode=mode, phase=phase, request_key=key)
    return True
