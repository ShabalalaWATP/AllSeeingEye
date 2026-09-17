"""Conservative admission for splitting a confirmed exhausted legacy final context."""

import re
from typing import Any

from ase.application.report_jobs.budget import (
    MAX_CALLS,
    MAX_OUTPUT_TOKENS,
    output_used,
    token_count,
)
from ase.application.report_jobs.stage_budget import PLAN_KEY, POLICY_KEY
from ase.application.reports.sections.synthesis_contracts import (
    CONTEXT,
    CONTEXT_PARTS,
    JUDGEMENTS,
    SCHEMA_NAMES,
    output_limit_for,
)
from ase.application.reports.templates import template_for
from ase.domain.errors import InvalidRequest
from ase.domain.llm import MAX_OUTPUT_TOKENS as MAX_PROFILE_OUTPUT
from ase.domain.llm import MIN_OUTPUT_TOKENS


def _saved(
    sections: dict[str, Any], packet: str, identity: str, parent: str
) -> dict[str, Any] | None:
    row = sections.get(f"{packet}:{identity}")
    if type(row) is not dict:
        return None
    body = row.get("payload")
    if (
        row.get("packet_digest") != packet
        or row.get("section_id") != identity
        or type(body) is not dict
        or body.get("id") != identity
        or body.get("kind") != "synthesis"
        or body.get("parent") != parent
    ):
        return None
    return row


def _confirmed(calls: list[Any]) -> bool:
    for row in calls:
        if type(row) is not dict or token_count(row.get("completion_tokens")) is None:
            return False
        if row.get("status") == "completed" and row.get("error") is None:
            continue
        if row.get("status") != "failed" or row.get("error") not in (
            "token_budget_exhausted",
            "not_dispatched",
        ):
            return False
        if row.get("error") == "not_dispatched" and row.get("completion_tokens") != 0:
            return False
    return True


def can_split_context(payload: dict[str, Any]) -> bool:
    """Offer new child calls only; never clear old hashes, reservations or frozen inputs.

    An existing opted-in stage plan cannot be enlarged by this legacy exception.
    Its owner must explicitly allocate the extra stages before a new job is admitted.
    """
    calls, sections, packet = (
        payload.get("calls"),
        payload.get("sections"),
        payload.get("current_packet"),
    )
    if (
        PLAN_KEY in payload
        or POLICY_KEY in payload
        or type(calls) is not list
        or not calls
        or len(calls) > MAX_CALLS
        or type(sections) is not dict
        or len(sections) > 64
        or type(packet) is not str
        or re.fullmatch(r"[0-9a-f]{64}", packet) is None
        or not _confirmed(calls)
        or any(
            type(row) is not dict
            or row.get("status") not in ("completed", "split", "incomplete")
            or (
                row.get("packet_digest") == packet
                and row.get("section_id") != CONTEXT
                and row.get("status") == "incomplete"
            )
            for row in sections.values()
        )
    ):
        return False
    parent = _saved(sections, packet, CONTEXT, "synthesis")
    judgements = _saved(sections, packet, JUDGEMENTS, "synthesis")
    if (
        parent is None
        or parent.get("status") != "incomplete"
        or parent.get("reason") != "token_budget_exhausted"
        or judgements is None
        or judgements.get("status") != "completed"
        or not any(
            row.get("schema") == "report_context"
            and row.get("status") == "failed"
            and row.get("error") == "token_budget_exhausted"
            for row in calls
        )
    ):
        return False
    missing = []
    for identity in CONTEXT_PARTS:
        if f"{packet}:{identity}" not in sections:
            missing.append(identity)
            continue
        child = _saved(sections, packet, identity, CONTEXT)
        if child is None or child.get("status") != "completed":
            return False
    if not missing:
        return False
    if any(
        row.get("error") == "token_budget_exhausted"
        and row.get("schema") in tuple(SCHEMA_NAMES[identity] for identity in CONTEXT_PARTS)
        for row in calls
    ):
        return False
    return _reservation_room(payload, calls, missing)


def _reservation_room(payload: dict[str, Any], calls: list[Any], missing: list[str]) -> bool:
    """Both remaining child reservations must fit the original model and lifetime limits."""
    try:
        frozen = payload["input"]
        role = template_for(frozen["template_id"]).role.value
        profiles = frozen["routing"]["profiles"]
        if type(profiles) is not list or not 1 <= len(profiles) <= 16:
            return False
        selected = [row for row in profiles if type(row) is dict and row.get("role") == role]
        if len(selected) != 1:
            return False
        limit = selected[0]["max_output_tokens"]
        if type(limit) is not int or not MIN_OUTPUT_TOKENS <= limit <= MAX_PROFILE_OUTPUT:
            return False
        required = sum(min(limit, output_limit_for(identity)) for identity in missing)
        return (
            len(calls) + len(missing) <= MAX_CALLS
            and output_used(payload) + required <= MAX_OUTPUT_TOKENS
        )
    except (KeyError, TypeError, ValueError, InvalidRequest):
        return False
