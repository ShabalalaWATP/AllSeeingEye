"""Preserve other people's authored revisions, including identity stored in payloads."""

import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

_REQUIRED_AUTHOR = frozenset(
    {
        "claim_revisions",
        "identity_decision_revisions",
        "relationship_review_revisions",
        "source_review_snapshots",
    }
)


def authorship_blocker(name: str, row: Mapping[str, Any], owner: UUID) -> str | None:
    if name not in _REQUIRED_AUTHOR | {"source_review_revisions", "report_ledger_entries"}:
        return None
    try:
        raw = row["payload"]
        payload = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(payload, dict):
            raise ValueError("Invalid author record")
        if name in _REQUIRED_AUTHOR:
            author = payload["authored_by"]
        elif name == "source_review_revisions":
            author = payload["review"]["assessor_id"]
        elif row["entry_kind"] == "forecast_decision":
            if payload.get("method") in {"verified_threshold", "clock"}:
                return None
            if payload.get("method") != "reviewer":
                raise ValueError("Invalid forecast decision method")
            author = payload["actor_id"]
        else:
            return None
        if UUID(str(author)) != owner:
            return "other_person_authored_revision"
    except (ValueError, TypeError, KeyError):
        return "unverifiable_revision_authorship"
    return None
