"""Per-depth original-attempt cap inside the shared frozen source phase."""

from typing import Any

from ase.application.research.phase_ledger import (
    LEDGER_KEY,
    PhaseLedgerError,
    ReservationDecision,
    operation_count_with_prefix,
    reserve_operation,
)
from ase.domain.research import ResearchMode

MAX_DOCUMENTS = {ResearchMode.QUICK: 2, ResearchMode.DETAILED: 6, ResearchMode.ADVANCED: 10}


def reserve_original(
    payload: dict[str, Any], mode: ResearchMode, request_key: str
) -> ReservationDecision:
    if not request_key.startswith("original:") or LEDGER_KEY not in payload:
        raise PhaseLedgerError("Original source-phase ledger is absent")
    count = operation_count_with_prefix(payload, mode=mode, phase="initial", prefix="original:")
    if count >= MAX_DOCUMENTS[mode]:
        operations = payload[LEDGER_KEY]["phases"]["initial"]["operations"]
        if request_key in operations:
            return reserve_operation(payload, mode=mode, phase="initial", request_key=request_key)
        return ReservationDecision("denied", False, 0, "document_cap")
    return reserve_operation(payload, mode=mode, phase="initial", request_key=request_key)
