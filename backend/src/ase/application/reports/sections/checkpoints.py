"""Revalidate saved step bodies and bind them to server-owned display metadata."""

from typing import Any, Literal

from ase.application.ports.section_checkpoints import SectionCheckpoint, SectionCheckpoints
from ase.application.reports.sections.contracts import validate_step
from ase.application.reports.sections.planning import Topic
from ase.application.reports.sections.synthesis_contracts import (
    ALL_PARTS,
    CONTEXT,
    CONTEXT_PARTS,
    TITLES,
    validate_aggregate_limits,
    validate_part,
)


def metadata(topic: Topic | None, labels: tuple[str, ...]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "id": topic.id if topic else "synthesis",
        "title": topic.title if topic else "Final synthesis",
        "kind": "topic" if topic else "synthesis",
        "evidence_labels": list(labels),
        "parent": topic.parent if topic else None,
    }
    if topic and topic.requirement_evidence:
        value["requirement_evidence"] = [
            {"requirement_id": requirement_id, "evidence_labels": list(evidence_labels)}
            for requirement_id, evidence_labels in topic.requirement_evidence
        ]
    return value


def synthesis_metadata(part: str, labels: tuple[str, ...]) -> dict[str, Any]:
    return {
        **metadata(None, labels),
        "id": part,
        "title": TITLES[part],
        "parent": CONTEXT if part in CONTEXT_PARTS else "synthesis",
    }


def read_body(
    checkpoint: SectionCheckpoint,
    expected: dict[str, Any],
    eeis: frozenset[str],
    *,
    previous_exists: bool = False,
    research_mode: object = None,
) -> dict[str, Any]:
    payload = checkpoint.payload
    if (
        not isinstance(payload, dict)
        or set(payload) != {*expected, "body"}
        or any(payload.get(key) != value for key, value in expected.items())
    ):
        raise ValueError("Checkpoint metadata does not match its frozen section")
    if expected["id"] in ALL_PARTS:
        return validate_part(
            payload["body"],
            part=expected["id"],
            labels=frozenset(expected["evidence_labels"]),
            eeis=eeis,
            previous_exists=previous_exists,
            research_mode=research_mode,
        )
    body = validate_step(
        payload["body"],
        synthesis=expected["kind"] == "synthesis",
        labels=frozenset(expected["evidence_labels"]),
        eeis=eeis,
    )
    if expected["kind"] == "synthesis":
        validate_aggregate_limits(body, research_mode=research_mode)
    return body


async def write_state(
    checkpoints: SectionCheckpoints,
    digest: str,
    expected: dict[str, Any],
    status: Literal["running", "completed", "split", "incomplete"],
    *,
    body: dict[str, Any] | None = None,
    reason: str | None = None,
    children: tuple[str, ...] = (),
) -> None:
    payload = dict(expected)
    if body is not None:
        payload["body"] = body
    if children:
        payload["children"] = list(children)
    if status not in ("running", "completed", "split", "incomplete"):
        raise ValueError("Unknown checkpoint state")
    await checkpoints.save(
        digest,
        str(expected["id"]),
        SectionCheckpoint(
            status=status,
            payload=payload,
            reason=reason,
        ),
    )
