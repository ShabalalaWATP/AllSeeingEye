"""Bounded canonical domain serialisation with type and hash verification."""

import hashlib
import json
from typing import Any, cast

from pydantic import TypeAdapter

from ase.domain.forecast_decisions import ForecastDecision
from ase.domain.forecast_ledger import ForecastVersion
from ase.domain.indicator_ledger import IndicatorReading, IndicatorVersion
from ase.domain.report_ledgers import LedgerEntry

MAX_LEDGER_ENTRY_BYTES = 16 * 1024

# Each registry entry validates one concrete variant before it crosses this union boundary.
_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "forecast_version": TypeAdapter(ForecastVersion),
    "forecast_decision": TypeAdapter(ForecastDecision),
    "indicator_version": TypeAdapter(IndicatorVersion),
    "indicator_reading": TypeAdapter(IndicatorReading),
}
_KINDS = {
    ForecastVersion: "forecast_version",
    ForecastDecision: "forecast_decision",
    IndicatorVersion: "indicator_version",
    IndicatorReading: "indicator_reading",
}


def encode_entry(value: LedgerEntry) -> tuple[str, str, str, int]:
    kind = _KINDS.get(type(value))
    if kind is None:
        raise ValueError("Unsupported ledger entry type")
    payload = _ADAPTERS[kind].dump_json(value).decode("utf-8")
    encoded = payload.encode("utf-8")
    if not 2 <= len(encoded) <= MAX_LEDGER_ENTRY_BYTES:
        raise ValueError("Ledger entry exceeds its retained size bound")
    return kind, payload, hashlib.sha256(encoded).hexdigest(), len(encoded)


def decode_entry(kind: str, payload: str, digest: str, size: int) -> LedgerEntry:
    adapter = _ADAPTERS.get(kind)
    if adapter is None or type(payload) is not str or type(size) is not int:
        raise ValueError("Invalid ledger entry record")
    encoded = payload.encode("utf-8")
    if (
        not 2 <= len(encoded) <= MAX_LEDGER_ENTRY_BYTES
        or len(encoded) != size
        or hashlib.sha256(encoded).hexdigest() != digest
    ):
        raise ValueError("Ledger entry integrity failed")
    value = cast(LedgerEntry, adapter.validate_json(payload, strict=True))
    # A decoded record may not silently discard a forged or future unknown field.
    if json.loads(adapter.dump_json(value)) != json.loads(payload):
        raise ValueError("Ledger entry fields do not match the pinned schema")
    return value
