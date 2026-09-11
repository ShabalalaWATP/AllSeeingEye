"""Small progress summaries and explicit public fields, never whole checkpoints."""

from typing import Any

from ase.application.report_jobs.budget import (
    MAX_CALLS,
    MAX_OUTPUT_TOKENS,
    output_used,
    token_count,
)
from ase.application.report_jobs.controls import NON_RESUMABLE_ERRORS
from ase.application.reports.templates import template_for
from ase.domain.errors import InvalidRequest
from ase.domain.report_jobs import ReportJob
from ase.domain.reports import MAX_ITEM_CHARS, MAX_LIST, MAX_SECTION_CHARS

_ERRORS = {
    "interrupted": "The previous call was interrupted. Its reserved allowance is retained.",
    "interrupted_uncertain": "Generation was interrupted. Review the saved work before resuming.",
    "provider_error": "The provider could not complete this step. Saved sections are retained.",
    "token_budget_exhausted": "This step used its output allowance before completing.",
    "budget_exhausted": "This report has reached its lifetime call or output allowance.",
    "report_job_budget_exhausted": "This report has reached its lifetime call or output allowance.",
    "profile_changed": "The saved model settings have changed. Start a new report.",
    "model_changed": "The saved model settings have changed. Start a new report.",
    "routing_changed": "The model assignment has changed. Start a new report.",
    "template_changed": "The report template has changed. Start a new report.",
    "source_disabled": "A source used by this report is no longer available.",
    "access_changed": "Access to the report's source material has changed.",
    "invalid_snapshot": "The saved report inputs could not be verified. Start a new report.",
    "invalid_packet": "The saved report inputs could not be verified. Start a new report.",
    "invalid_checkpoint": "A saved section could not be verified.",
    "invalid_section": "A generated section did not pass validation.",
    "invalid_synthesis": "The final assessment did not pass validation.",
    "insufficient_evidence": "The selected evidence does not support a complete assessment.",
    "input_limit": "This step's evidence exceeds the supported input size.",
    "time_limit": "This generation run reached its time limit. Saved sections are retained.",
    "section_token_budget_exhausted": (
        "Saved sections are retained. Start a smaller report to complete this assessment."
    ),
}


def error_message(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.startswith("section_") and value not in _ERRORS:
        value = value.removeprefix("section_")
    return (
        _ERRORS.get(value, "Generation paused because this step could not be safely completed.")
        if isinstance(value, str)
        else "The saved progress is unavailable."
    )


def _text(value: Any, limit: int = 2048) -> str:
    if (
        type(value) is not str
        or len(value) > limit
        or any(ord(char) < 32 and char not in "\n\t" for char in value)
    ):
        raise InvalidRequest("The saved report progress is unavailable.")
    return value


def _count(value: Any, limit: int = 2**31 - 1) -> int:
    if type(value) is not int or not 0 <= value <= limit:
        raise InvalidRequest("The saved report progress is unavailable.")
    return value


def current_sections(payload: dict[str, Any]) -> list[dict[str, Any]]:
    packet = payload.get("current_packet")
    sections = payload.get("sections", {})
    if type(sections) is not dict or len(sections) > 64:
        raise InvalidRequest("The saved report sections are unavailable.")
    if packet is None:
        return []
    if (
        type(packet) is not str
        or len(packet) != 64
        or any(char not in "0123456789abcdef" for char in packet)
    ):
        raise InvalidRequest("The saved report packet is unavailable.")
    result = []
    for key, value in sections.items():
        if type(value) is not dict:
            raise InvalidRequest("The saved report sections are unavailable.")
        if value.get("packet_digest") != packet:
            continue
        if key != f"{packet}:{value.get('section_id')}" or value.get("status") not in {
            "running",
            "completed",
            "split",
            "incomplete",
        }:
            raise InvalidRequest("The saved report section identity is unavailable.")
        result.append(value)
    # The combined parent is retained for cache compatibility, not a third piece
    # of completed work. Foreign-packet children must never hide a legacy result.
    if any(
        row.get("section_id") != "synthesis"
        and type(row.get("payload")) is dict
        and row["payload"].get("parent") == "synthesis"
        for row in result
    ):
        result = [row for row in result if row.get("section_id") != "synthesis"]
    synthesis_order = {"synthesis_judgements": 1, "synthesis_context": 2}
    return sorted(result, key=lambda row: synthesis_order.get(str(row.get("section_id")), 0))


def refresh_summary(payload: dict[str, Any]) -> None:
    """Update the bounded cache after each mutation; it contains no partial report prose."""
    frozen = payload.get("input", {})
    if type(frozen) is not dict:
        raise InvalidRequest("The saved report inputs are unavailable.")
    try:
        role = template_for(frozen["template_id"]).role.value
        profile = next(row for row in frozen["routing"]["profiles"] if row["role"] == role)
        model = _text(profile["model"])
        effort = profile["reasoning_effort"]
    except (KeyError, TypeError, ValueError, StopIteration):
        raise InvalidRequest("The saved report model summary is unavailable.") from None
    if effort is not None:
        effort = _text(effort, 40)
    sections = current_sections(payload)
    leaves = [row for row in sections if row["status"] != "split"]
    calls = payload.get("calls", [])
    if type(calls) is not list or len(calls) > MAX_CALLS:
        raise InvalidRequest("The saved report usage is unavailable.")
    payload["summary"] = {
        "model": model,
        "reasoning_effort": effort,
        "completed_sections": sum(row["status"] == "completed" for row in leaves),
        "total_sections": len(leaves),
        "in_flight_calls": sum(row.get("status") == "in_flight" for row in calls),
        "usage": {
            "calls": len(calls),
            "max_calls": MAX_CALLS,
            "output_tokens": output_used(payload),
            "output_allowance": MAX_OUTPUT_TOKENS,
            "uncertain_calls": sum(
                row.get("status") == "uncertain"
                or (
                    row.get("status") == "failed"
                    and token_count(row.get("completion_tokens")) is None
                )
                for row in calls
            ),
        },
    }


def _context_preview(body: dict[str, Any], *, split: bool) -> str | None:
    """Project accepted synthesis context as bounded text, never serialise nested data."""
    parts = []
    if "sourcing_statement" in body:
        parts.append("Sourcing: " + _text(body["sourcing_statement"], MAX_SECTION_CHARS))
    for field, prefix in (
        ("gaps", "Evidence gap"),
        ("collection_recommendations", "Collection recommendation"),
    ):
        values = body.get(field, [])
        if type(values) is not list or len(values) > (MAX_LIST if field == "gaps" else 8):
            raise InvalidRequest("The saved report context is unavailable.")
        for value in values:
            if field == "gaps":
                if type(value) is not dict:
                    raise InvalidRequest("The saved report context is unavailable.")
                text_value = value.get("text")
            else:
                text_value = value
            limit = 400 if split and field == "gaps" else MAX_ITEM_CHARS
            parts.append(prefix + ": " + _text(text_value, limit))
    return "\n\n".join(parts) or None


def _section(value: dict[str, Any]) -> dict[str, Any]:
    data = value.get("payload")
    if type(data) is not dict:
        raise InvalidRequest("The saved report section metadata is unavailable.")
    identity = _text(value.get("section_id"), 120)
    if data.get("id") != identity or data.get("kind") not in {"topic", "synthesis"}:
        raise InvalidRequest("The saved report section metadata is unavailable.")
    body = data.get("body") if value["status"] == "completed" else None
    reporting: list[str] = []
    assessment = None
    citations: set[str] = set()
    if body is not None:
        if type(body) is not dict:
            raise InvalidRequest("The saved report section body is unavailable.")
        rows = (
            body.get("reporting", []) if data["kind"] == "topic" else body.get("key_judgements", [])
        )
        paragraphs = body.get("assessment", [])
        if (
            type(rows) is not list
            or len(rows) > 5
            or type(paragraphs) is not list
            or len(paragraphs) > 1
        ):
            raise InvalidRequest("The saved report section text is unavailable.")
        allowed = data.get("evidence_labels", [])
        for row in [*rows, *paragraphs]:
            if type(row) is not dict:
                raise InvalidRequest("The saved report section text is unavailable.")
            names = (
                ("evidence",)
                if data["kind"] == "topic"
                else ("supporting_evidence", "contradicting_evidence")
            )
            for name in names:
                labels = row.get(name, [])
                if (
                    type(labels) is not list
                    or len(labels) > 100
                    or any(type(label) is not str or label not in allowed for label in labels)
                ):
                    raise InvalidRequest("The saved report section citations are unavailable.")
                citations.update(labels)
        text_key = "text" if data["kind"] == "topic" else "statement"
        reporting = [_text(row.get(text_key), 12_000) for row in rows]
        assessment = _text(paragraphs[0].get("text"), 12_000) if paragraphs else None
        if data["kind"] == "synthesis":
            assessment = _context_preview(body, split=identity == "synthesis_context")
    return {
        "id": identity,
        "title": _text(data.get("title"), 300),
        "kind": data["kind"],
        "status": value["status"],
        "reporting": reporting,
        "assessment": assessment,
        "citations": sorted(citations),
        "error": error_message(value.get("reason")),
    }


def job_view(job: ReportJob, *, detail: bool = True, can_control: bool = True) -> dict[str, Any]:
    summary = job.payload.get("summary")
    if type(summary) is not dict or type(summary.get("usage")) is not dict:
        raise InvalidRequest("The saved report progress is unavailable.")
    if "in_flight_calls" not in summary and "input" in job.payload and "calls" in job.payload:
        # Older detail snapshots can be projected accurately without a migration
        # or rewriting saved progress. Thin lists still use only their small cache.
        projection = dict(job.payload)
        refresh_summary(projection)
        summary = projection["summary"]
    usage = {
        key: _count(summary["usage"].get(key))
        for key in (
            "calls",
            "max_calls",
            "output_tokens",
            "output_allowance",
            "uncertain_calls",
        )
    }
    if job.status not in {"queued", "running"}:
        # A stopped job cannot confirm an outstanding request's outcome. Its
        # reservation already remains in output_tokens, irrespective of status.
        usage["uncertain_calls"] += _count(summary.get("in_flight_calls", 0), MAX_CALLS)
    effort = summary.get("reasoning_effort")
    return {
        "id": job.id,
        "revision": job.revision,
        "title": job.title,
        "status": job.status,
        "stage": job.stage,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "team_id": job.team_id,
        "report_id": job.report_id if job.status in {"completed", "needs_review"} else None,
        "model": _text(summary.get("model")),
        "reasoning_effort": None if effort is None else _text(effort, 40),
        "error": error_message(job.error),
        "can_resume": can_control
        and job.status in {"paused", "failed"}
        and job.error not in NON_RESUMABLE_ERRORS
        and usage["calls"] < MAX_CALLS
        and usage["output_tokens"] < MAX_OUTPUT_TOKENS,
        "completed_sections": _count(summary.get("completed_sections"), 64),
        "total_sections": _count(summary.get("total_sections"), 64),
        "sections": [_section(row) for row in current_sections(job.payload)] if detail else [],
        "usage": usage,
    }
