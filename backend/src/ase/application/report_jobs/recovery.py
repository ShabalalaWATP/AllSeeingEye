"""Recover a known section failure only from unambiguous, settled checkpoints."""

import re
from typing import Any

from ase.application.report_jobs.budget_limits import MAX_CALLS

_REASONS = frozenset(
    {
        "invalid_section",
        "invalid_synthesis",
        "invalid_checkpoint",
        "invalid_packet",
        "input_limit",
        "insufficient_evidence",
        "token_budget_exhausted",
    }
)
SECTION_FAILURES = frozenset(f"section_{reason}" for reason in _REASONS)


def expired_failure(payload: dict[str, Any]) -> str:
    """This changes the displayed reason only; recovery never schedules a paid retry.

    Old packets, ambiguous failures and any unresolved call or section retain the
    conservative interruption reason. A provider completion need not include usage
    counts to confirm that its response was received and durably settled.
    """
    unknown = "interrupted_uncertain"
    calls = payload.get("calls")
    if type(calls) is not list or not calls or len(calls) > MAX_CALLS:
        return unknown
    if any(
        type(call) is not dict or call.get("status") != "completed" or call.get("error") is not None
        for call in calls
    ):
        return unknown
    packet, sections = payload.get("current_packet"), payload.get("sections")
    if (
        type(packet) is not str
        or re.fullmatch(r"[0-9a-f]{64}", packet) is None
        or type(sections) is not dict
        or any(
            type(row) is not dict or row.get("status") not in ("completed", "split", "incomplete")
            for row in sections.values()
        )
    ):
        return unknown
    failures = []
    for key, section in sections.items():
        if section.get("packet_digest") != packet or section.get("status") != "incomplete":
            continue
        identity, reason, body = (
            section.get("section_id"),
            section.get("reason"),
            section.get("payload"),
        )
        if (
            type(identity) is not str
            or key != f"{packet}:{identity}"
            or type(reason) is not str
            or reason not in _REASONS
            or type(body) is not dict
            or body.get("id") != identity
            or body.get("kind") not in ("topic", "synthesis")
        ):
            return unknown
        failures.append(f"section_{reason}")
    return failures[0] if len(failures) == 1 else unknown
