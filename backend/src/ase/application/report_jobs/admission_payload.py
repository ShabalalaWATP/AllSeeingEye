"""The initial frozen payload of an admitted report job, built before any persistence."""

from typing import Any

from ase.application.report_jobs.fresh_web_allocation import freeze_web_discovery
from ase.application.report_jobs.views import refresh_summary
from ase.application.reports.request import ReportRequest
from ase.application.research.phase_ledger import LEDGER_KEY, new_phase_ledger


def initial_payload(request: ReportRequest, digest: str, frozen: dict[str, Any]) -> dict[str, Any]:
    """Frozen inputs, request identity, an empty checkpoint and any research ledgers."""
    payload: dict[str, Any] = {
        "schema_version": 1,
        "input": frozen,
        "request_digest": digest,
        "sections": {},
        "calls": [],
        "collection": None,
    }
    if request.research_mode is not None:
        payload[LEDGER_KEY] = new_phase_ledger(request.research_mode)
    if request.research_web_search:
        freeze_web_discovery(payload)
    refresh_summary(payload)
    return payload
